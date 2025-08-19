#!/usr/bin/env python3
"""
Test REAL composition - actually verify one proof inside another guest.
"""

import sys
import os
from pathlib import Path

def test_real_composition():
    """Test actual proof composition with nested verification."""
    print("Testing REAL proof composition (proof of proof)")
    print("=" * 60)
    
    test_passed = True
    
    try:
        import pyr0
        from pyr0 import serialization
        
        # Step 1: Build the outer guest that will verify inner proofs
        print("\n1. Building outer guest for composition...")
        outer_guest_dir = Path("test_composition_guest")
        
        try:
            outer_elf_path = pyr0.build_guest(outer_guest_dir)
            print(f"   ✓ Built outer guest at: {outer_elf_path}")
            
            with open(outer_elf_path, "rb") as f:
                outer_elf = f.read()
            outer_image = pyr0.load_image(outer_elf)
            outer_image_id = outer_image.id
            print(f"   ✓ Loaded outer image, ID: {outer_image_id.hex()[:16]}...")
            
        except Exception as e:
            print(f"   ✗ Failed to build outer guest: {e}")
            test_passed = False
            return test_passed
        
        # Step 2: Generate an inner proof (Ed25519 verification)
        print("\n2. Generating inner proof (Ed25519 signature verification)...")
        
        inner_elf_path = Path("demo/ed25519_demo_guest/target/riscv32im-risc0-zkvm-elf/release/ed25519-guest-input")
        if not inner_elf_path.exists():
            print(f"   ⚠ Building inner guest first...")
            inner_elf_path = pyr0.build_guest("demo/ed25519_demo_guest")
            
        with open(inner_elf_path, "rb") as f:
            inner_elf = f.read()
        inner_image = pyr0.load_image(inner_elf)
        inner_image_id = inner_image.id
        
        # Create input for Ed25519 verification (valid signature)
        pk = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        msg = b""
        inner_input = serialization.ed25519_input(pk, sig, msg)
        
        print("   Generating inner proof...")
        inner_receipt = pyr0.prove(inner_image, inner_input)
        print(f"   ✓ Inner proof generated, journal size: {len(inner_receipt.journal)} bytes")
        
        # Verify the inner proof works standalone
        inner_receipt.verify(inner_image_id)
        print("   ✓ Inner proof verified successfully")
        
        # Step 3: Test composition - verify inner proof inside outer guest
        print("\n3. Testing composition (outer guest verifies inner proof)...")
        
        # Safety check
        if not inner_receipt.verify_image_id(inner_image_id):
            print("   ✗ Image ID mismatch!")
            test_passed = False
            return test_passed
        print("   ✓ Image ID check passed")
        
        # Prepare composition input
        inner_bytes = inner_receipt.to_inner_bytes()
        additional_data = b"test additional data for outer program"
        
        outer_input = serialization.composition_input(
            inner_bytes,
            inner_image_id,
            additional_data
        )
        
        print(f"   Composition input size: {len(outer_input)} bytes")
        print("   Generating outer proof (this verifies the inner proof)...")
        
        try:
            # This is the real test - the outer guest will verify the inner proof
            outer_receipt = pyr0.prove(outer_image, outer_input)
            print(f"   ✓ Outer proof generated! Journal size: {len(outer_receipt.journal)} bytes")
            
            # Verify the outer proof
            outer_receipt.verify(outer_image_id)
            print("   ✓ Outer proof verified successfully")
            
            # Check the outer journal to see what it recorded
            outer_journal = outer_receipt.journal
            if len(outer_journal) >= 16:
                # Parse the output from our test guest
                import struct
                marker = struct.unpack('<I', outer_journal[0:4])[0]
                inner_result = struct.unpack('<I', outer_journal[4:8])[0]
                inner_journal_size = struct.unpack('<I', outer_journal[8:12])[0]
                additional_size = struct.unpack('<I', outer_journal[12:16])[0]
                
                print(f"\n   Outer guest output:")
                print(f"     - Marker: {marker} (expected 42)")
                print(f"     - Inner verification result: {inner_result}")
                print(f"     - Inner journal size seen: {inner_journal_size}")
                print(f"     - Additional data size: {additional_size}")
                
                if marker != 42:
                    print("   ✗ Unexpected marker from outer guest")
                    test_passed = False
                else:
                    print("   ✓ Outer guest executed correctly")
                    
                if inner_result == 1:
                    print("   ✓ Inner proof's Ed25519 verification was successful")
                else:
                    print("   ✗ Inner proof's Ed25519 verification failed")
                    test_passed = False
                    
                if additional_size == len(additional_data):
                    print("   ✓ Additional data was received correctly")
                else:
                    print(f"   ✗ Additional data size mismatch: {additional_size} vs {len(additional_data)}")
                    test_passed = False
            else:
                print("   ✗ Outer journal too short")
                test_passed = False
                
        except Exception as e:
            print(f"   ✗ Composition failed: {e}")
            import traceback
            traceback.print_exc()
            test_passed = False
        
        # Step 4: Test failure case - wrong image ID
        print("\n4. Testing composition with wrong image ID (should fail)...")
        
        wrong_image_id = b"\xFF" * 32
        wrong_input = serialization.composition_input(
            inner_bytes,
            wrong_image_id,  # Wrong ID - verification should fail
            additional_data
        )
        
        try:
            # This should fail because the inner proof doesn't match the expected ID
            outer_receipt = pyr0.prove(outer_image, wrong_input)
            # If we get here, something is wrong
            print("   ✗ Should have failed with wrong image ID!")
            test_passed = False
        except Exception as e:
            # Expected to fail
            if "verification failed" in str(e).lower() or "panicked" in str(e).lower():
                print(f"   ✓ Correctly failed with wrong image ID")
            else:
                print(f"   ⚠ Failed but with unexpected error: {e}")
        
        return test_passed
        
    except ImportError as e:
        print(f"\n✗ Failed to import PyR0: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run real composition test."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 13 + "Real Composition Test (Proof of Proof)" + " " * 6 + "║")
    print("╚" + "=" * 58 + "╝")
    
    test_passed = test_real_composition()
    
    print("\n" + "=" * 60)
    if test_passed:
        print("✅ Real composition test PASSED!")
        print("\nWe successfully:")
        print("  1. Generated an inner proof (Ed25519 verification)")
        print("  2. Passed it to an outer guest program")
        print("  3. The outer guest verified the inner proof")
        print("  4. Generated an outer proof of the verification")
        print("  5. Verified the outer proof")
        print("\nThis demonstrates true proof composition!")
        return 0
    else:
        print("✗ Real composition test FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())