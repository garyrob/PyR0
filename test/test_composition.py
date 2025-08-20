#!/usr/bin/env python3
"""
Test proof composition using RISC Zero's assumption-based model.

This demonstrates how to:
1. Create an inner proof
2. Pass it as an assumption to an outer proof
3. Verify the composition chain
"""

import pyr0
from pathlib import Path
import subprocess
import sys

def build_inner_guest():
    """Build the inner guest that performs addition."""
    inner_dir = Path("test_inner_guest")
    
    # Create inner guest if needed
    if not inner_dir.exists():
        print("Creating inner guest...")
        inner_dir.mkdir()
        
        # Create Cargo.toml
        (inner_dir / "Cargo.toml").write_text("""[package]
name = "test-inner-guest"
version = "0.1.0"
edition = "2021"

[dependencies]
risc0-zkvm = { version = "1.2" }

[workspace]
""")
        
        # Create src/main.rs
        src_dir = inner_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.rs").write_text("""
use risc0_zkvm::guest::env;

fn main() {
    // Read two numbers
    let a: u32 = env::read();
    let b: u32 = env::read();
    
    // Compute sum
    let sum = a + b;
    
    // Commit the sum to the journal
    env::commit(&sum);
}
""")
        
        # Build the guest
        print("Building inner guest...")
        subprocess.run(["cargo", "build", "--release"], cwd=inner_dir, check=True)
    
    # Build and return path
    return pyr0.build_guest(inner_dir, release=True)

def build_outer_guest():
    """Build the outer guest that verifies the inner proof."""
    outer_dir = Path("test_outer_guest")
    
    # Create outer guest if needed
    if not outer_dir.exists():
        print("Creating outer guest...")
        outer_dir.mkdir()
        
        # Create Cargo.toml
        (outer_dir / "Cargo.toml").write_text("""[package]
name = "test-outer-guest"
version = "0.1.0"
edition = "2021"

[dependencies]
risc0-zkvm = { version = "1.2" }

[workspace]
""")
        
        # Create src/main.rs
        src_dir = outer_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.rs").write_text("""
use risc0_zkvm::guest::env;

fn main() {
    // Read the expected sum from the inner proof
    let expected_sum: u32 = env::read();
    
    // Read the image ID of the inner guest
    let inner_image_id: [u8; 32] = env::read();
    
    // Create expected journal (inner guest commits a u32)
    let expected_journal = risc0_zkvm::serde::to_vec(&expected_sum).unwrap();
    
    // Verify the assumption (inner proof)
    // This will be checked when the outer proof is verified
    env::verify(inner_image_id, &expected_journal).unwrap();
    
    // Do some additional computation with the verified sum
    let result = expected_sum * 2;
    
    // Commit the result
    env::commit(&result);
}
""")
        
        # Build the guest
        print("Building outer guest...")
        subprocess.run(["cargo", "build", "--release"], cwd=outer_dir, check=True)
    
    # Build and return path
    return pyr0.build_guest(outer_dir, release=True)

def test_composition_with_composer():
    """Test composition using the Composer API."""
    print("Testing RISC Zero Proof Composition with Composer")
    print("=" * 60)
    
    test_passed = True
    
    try:
        
        # Build both guests
        print("\n1. Building guests...")
        inner_elf_path = build_inner_guest()
        outer_elf_path = build_outer_guest()
        
        # Load images
        print("\n2. Loading images...")
        inner_elf = inner_elf_path.read_bytes()
        outer_elf = outer_elf_path.read_bytes()
        
        inner_image = pyr0.load_image(inner_elf)
        outer_image = pyr0.load_image(outer_elf)
        
        # Compute image IDs
        inner_image_id_hex = pyr0.compute_image_id_hex(inner_elf)
        inner_image_id_bytes = bytes.fromhex(inner_image_id_hex)
        print(f"Inner image ID: {inner_image_id_hex[:16]}...")
        print(f"Outer image ID: {pyr0.compute_image_id_hex(outer_elf)[:16]}...")
        
        # Create inner proof (must be succinct for composition)
        print("\n3. Creating inner proof (3 + 5 = 8)...")
        a, b = 3, 5
        inner_input = pyr0.serialization.to_u32(a) + pyr0.serialization.to_u32(b)
        inner_receipt = pyr0.prove_succinct(inner_image, inner_input)
        
        # Extract the sum from the journal
        import struct
        # The journal contains the serialized u32 sum (4 bytes, little-endian)
        journal_bytes = inner_receipt.journal_bytes
        sum_value = struct.unpack('<I', journal_bytes[:4])[0]
        print(f"Inner proof created: sum = {sum_value}")
        print(f"Inner proof size: {inner_receipt.seal_size} bytes")
        print(f"Inner proof kind: {inner_receipt.kind}")
        print(f"Is unconditional: {inner_receipt.is_unconditional}")
        
        # Create outer proof with assumption
        print("\n4. Creating outer proof with assumption...")
        
        # Create Composer with the inner receipt as an assumption
        comp = pyr0.Composer(outer_image)
        comp.assume(inner_receipt)
        
        # Tell the Composer what env::verify() calls to expect
        # The outer guest will verify the inner proof with the expected journal
        comp.expect_verification(inner_image_id_bytes, journal_bytes)
        
        # Write inputs for the outer guest using typed writers
        comp.write_u32(sum_value)  # Expected sum (4 bytes)
        comp.write_image_id(inner_image_id_bytes)  # Inner image ID (32 bytes)
        
        # Prove with the assumption (defaults to succinct to resolve assumptions)
        outer_receipt = comp.prove()
        
        # Extract result from outer journal
        outer_journal = outer_receipt.journal_bytes
        result = struct.unpack('<I', outer_journal[:4])[0]
        print(f"Outer proof created: result = {result} (sum * 2)")
        print(f"Outer proof size: {outer_receipt.seal_size} bytes")
        
        # Verify the outer proof
        print("\n5. Verifying composition...")
        try:
            # Use the unified verify method with the image
            outer_receipt.verify(outer_image)
            print("✅ Composition verified successfully!")
            print("   The outer proof proves:")
            print(f"   - The inner proof is valid (3 + 5 = 8)")
            print(f"   - The outer computation is correct (8 * 2 = 16)")
            print(f"   - Proof kind: {outer_receipt.kind}")
            print(f"   - All assumptions resolved: {outer_receipt.assumption_count == 0}")
        except pyr0.VerificationError as e:
            print(f"❌ Verification failed: {e}")
            test_passed = False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            test_passed = False
        
        # Test invalid assumption
        print("\n6. Testing invalid assumption (should fail)...")
        try:
            # Try to create outer proof with wrong expected sum
            comp_bad = pyr0.Composer(outer_image)
            comp_bad.assume(inner_receipt)
            comp_bad.write_u32(999)  # Wrong sum!
            comp_bad.write_image_id(inner_image_id_bytes)
            
            outer_receipt_bad = comp_bad.prove()
            print("❌ Should have failed with wrong assumption!")
            test_passed = False
        except (pyr0.CompositionError, pyr0.PreflightError) as e:
            print(f"✅ Correctly rejected invalid assumption: {str(e)[:100]}...")
        except Exception as e:
            print(f"✅ Rejected with: {type(e).__name__}: {str(e)[:100]}...")
        
        return test_passed
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed

def main():
    """Run composition tests."""
    print("\n" + "=" * 60)
    print("" + " " * 8 + "RISC ZERO PROOF COMPOSITION TEST" + " " * 19)
    print("=" * 60)
    
    test_passed = test_composition_with_composer()
    
    if test_passed:
        print("\n" + "=" * 60)
        print("SUCCESS: Composition with Composer API works correctly!")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAILED: Some tests failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())