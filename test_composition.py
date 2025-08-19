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

def test_composition_with_assumptions():
    """Test composition using ExecutorEnv with assumptions."""
    print("Testing RISC Zero Proof Composition with Assumptions")
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
        
        # Create inner proof
        print("\n3. Creating inner proof (3 + 5 = 8)...")
        a, b = 3, 5
        inner_input = pyr0.serialization.to_u32(a) + pyr0.serialization.to_u32(b)
        inner_receipt = pyr0.prove(inner_image, inner_input)
        
        # Extract the sum from the journal
        import struct
        # The journal contains the serialized u32 sum (4 bytes, little-endian)
        journal_bytes = inner_receipt.journal_bytes
        sum_value = struct.unpack('<I', journal_bytes[:4])[0]
        print(f"Inner proof created: sum = {sum_value}")
        print(f"Inner proof size: {inner_receipt.seal_size} bytes")
        
        # Create outer proof with assumption
        print("\n4. Creating outer proof with assumption...")
        
        # Create ExecutorEnv with the inner receipt as an assumption
        env = pyr0.ExecutorEnv()
        env.add_assumption(inner_receipt)
        
        # Write inputs for the outer guest
        env.write(pyr0.serialization.to_u32(sum_value))  # Expected sum
        env.write(inner_image_id_bytes)  # Inner image ID as [u8; 32]
        
        # Prove with the assumption
        outer_receipt = pyr0.prove_with_env(outer_image, env)
        
        # Extract result from outer journal
        outer_journal = outer_receipt.journal_bytes
        result = struct.unpack('<I', outer_journal[:4])[0]
        print(f"Outer proof created: result = {result} (sum * 2)")
        print(f"Outer proof size: {outer_receipt.seal_size} bytes")
        
        # Verify the outer proof
        print("\n5. Verifying composition...")
        outer_image_id = pyr0.compute_image_id_hex(outer_elf)
        try:
            outer_receipt.verify_hex(outer_image_id)
            print("✅ Composition verified successfully!")
            print("   The outer proof proves:")
            print(f"   - The inner proof is valid (3 + 5 = 8)")
            print(f"   - The outer computation is correct (8 * 2 = 16)")
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            test_passed = False
        
        # Test invalid assumption
        print("\n6. Testing invalid assumption (should fail)...")
        try:
            # Try to create outer proof with wrong expected sum
            env_bad = pyr0.ExecutorEnv()
            env_bad.add_assumption(inner_receipt)
            env_bad.write(pyr0.serialization.to_u32(999))  # Wrong sum!
            env_bad.write(inner_image_id_bytes)
            
            outer_receipt_bad = pyr0.prove_with_env(outer_image, env_bad)
            print("❌ Should have failed with wrong assumption!")
            test_passed = False
        except Exception as e:
            print(f"✅ Correctly rejected invalid assumption: {str(e)[:100]}...")
        
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
    
    test_passed = test_composition_with_assumptions()
    
    if test_passed:
        print("\n" + "=" * 60)
        print("SUCCESS: Composition with assumptions works correctly!")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAILED: Some tests failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())