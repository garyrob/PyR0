#!/usr/bin/env python3
"""
Test CBOR serialization with PyR0's Composer API.

This test demonstrates the recommended pattern for passing structured data
to RISC Zero guests using CBOR encoding.
"""

import cbor2
import pyr0
from pathlib import Path
import sys

def test_cbor_serialization():
    """Test that CBOR serialization works correctly with Composer."""
    print("Testing CBOR Serialization with Composer")
    print("=" * 60)
    
    test_passed = True
    
    try:
        # Build the test guest
        print("\n1. Building CBOR test guest...")
        guest_dir = Path("test_cbor_guest")
        
        try:
            elf_path = pyr0.build_guest(guest_dir, "test-cbor-guest")
            print(f"   ✓ Built guest: {elf_path}")
            
            with open(elf_path, "rb") as f:
                elf_data = f.read()
        except (pyr0.GuestBuildFailedError, pyr0.ElfNotFoundError) as e:
            print(f"   ❌ Failed to build guest: {e}")
            return False
        
        # Load the image
        print("\n2. Loading guest image...")
        image = pyr0.load_image(elf_data)
        print(f"   ✓ Loaded image with ID: {image.id_hex[:16]}...")
        
        # Prepare test data - as a CBOR array to match Rust's numeric indices
        print("\n3. Preparing test data...")
        # The Rust struct uses #[n(0)] and #[n(1)], which expects a CBOR array
        # We'll create the data as [a_value, b_bytes]
        payload = [2, b"\x01\x02\x03"]  # Array format for numeric indices
        print(f"   Input data: a=2, b=b'\\x01\\x02\\x03' (as array)")
        
        # Encode to CBOR
        cbor_bytes = cbor2.dumps(payload, canonical=True)
        print(f"   CBOR encoded: {len(cbor_bytes)} bytes")
        print(f"   Hex: {cbor_bytes.hex()}")
        
        # Create composer and write CBOR data
        print("\n4. Creating proof with Composer...")
        comp = pyr0.Composer(image)
        comp.write_cbor(cbor_bytes)
        
        # Prove
        print("   Generating proof...")
        receipt = comp.prove()
        print(f"   ✓ Proof generated, journal size: {len(receipt.journal)} bytes")
        
        # Decode the output from the journal
        print("\n5. Verifying output...")
        output = cbor2.loads(receipt.journal)
        print(f"   Output: {output}")
        
        # The output is also an array: [sum, a_value, b_length, b_bytes]
        # Based on the Rust struct with #[n(0)], #[n(1)], #[n(2)], #[n(3)]
        expected_sum = 2 + (1 + 2 + 3)  # a + sum(b)
        
        if isinstance(output, list) and len(output) >= 4:
            sum_val, a_val, b_len, b_bytes = output[0], output[1], output[2], output[3]
            
            if sum_val != expected_sum:
                print(f"   ❌ Sum mismatch: expected {expected_sum}, got {sum_val}")
                test_passed = False
            else:
                print(f"   ✓ Sum correct: {expected_sum}")
            
            if a_val != 2:
                print(f"   ❌ 'a' value mismatch: expected 2, got {a_val}")
                test_passed = False
            else:
                print(f"   ✓ 'a' value correct: 2")
            
            if b_len != 3:
                print(f"   ❌ 'b' length mismatch: expected 3, got {b_len}")
                test_passed = False
            else:
                print(f"   ✓ 'b' length correct: 3")
            
            if b_bytes != b"\x01\x02\x03":
                print(f"   ❌ 'b' bytes mismatch: expected b'\\x01\\x02\\x03', got {b_bytes}")
                test_passed = False
            else:
                print(f"   ✓ 'b' bytes correct: b'\\x01\\x02\\x03'")
        else:
            print(f"   ❌ Output format unexpected: {type(output)}")
            test_passed = False
        
        # Verify the receipt with the image
        print("\n6. Verifying receipt...")
        try:
            receipt.verify(image)
            print("   ✓ Receipt verified successfully")
        except Exception as e:
            print(f"   ❌ Receipt verification failed: {e}")
            test_passed = False
        
        return test_passed
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the CBOR serialization test."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "CBOR Serialization Test Suite" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    test_passed = test_cbor_serialization()
    
    print("\n" + "=" * 60)
    if test_passed:
        print("✅ All CBOR serialization tests passed!")
        print("\nThis demonstrates the recommended pattern for complex data:")
        print("1. Encode your data with cbor2 in Python")
        print("2. Pass to guest with comp.write_cbor()")
        print("3. Decode in guest with minicbor")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())