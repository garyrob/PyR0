#!/usr/bin/env python3
"""
Test InputBuilder API for constructing guest input data.

This test demonstrates that InputBuilder can be used independently
of Composer for general guest communication.
"""

import pyr0
import cbor2
import struct
from pathlib import Path
import sys

def test_input_builder_standalone():
    """Test InputBuilder used directly with pyr0.prove()."""
    print("Testing InputBuilder API")
    print("=" * 60)
    
    try:
        # Build a simple test guest
        print("\n1. Building test guest...")
        guest_dir = Path("test_cbor_guest")
        
        elf_path = pyr0.build_guest(guest_dir, "test-cbor-guest")
        print(f"   ✓ Built guest: {elf_path}")
        
        with open(elf_path, "rb") as f:
            elf_data = f.read()
        
        # Load the image
        print("\n2. Loading guest image...")
        image = pyr0.load_image(elf_data)
        print(f"   ✓ Loaded image with ID: {image.id_hex[:16]}...")
        
        # Test 1: InputBuilder with CBOR
        print("\n3. Testing InputBuilder with CBOR...")
        builder = pyr0.InputBuilder()
        
        # Prepare test data as CBOR array
        payload = [2, b"\x01\x02\x03"]  # Array format for numeric indices
        cbor_bytes = cbor2.dumps(payload, canonical=True)
        
        # Use InputBuilder to write CBOR
        builder.write_cbor(cbor_bytes)
        
        # Build and prove
        input_data = builder.build()
        print(f"   Built input: {len(input_data)} bytes")
        
        receipt = pyr0.prove(image, input_data)
        print(f"   ✓ Proof generated with InputBuilder")
        
        # Verify output
        output = cbor2.loads(receipt.journal)
        expected_sum = 2 + (1 + 2 + 3)  # a + sum(b)
        
        if isinstance(output, list) and len(output) >= 4:
            sum_val = output[0]
            if sum_val == expected_sum:
                print(f"   ✓ Correct output: sum = {expected_sum}")
            else:
                print(f"   ❌ Wrong sum: expected {expected_sum}, got {sum_val}")
                return False
        else:
            print(f"   ❌ Unexpected output format")
            return False
        
        # Test 2: Method chaining
        print("\n4. Testing method chaining...")
        builder2 = pyr0.InputBuilder()
        
        # Chain multiple writes
        builder2.write_u32(100).write_u64(200).write_raw_bytes(b"\x00" * 8)
        
        chained_data = builder2.build()
        print(f"   ✓ Method chaining works: {len(chained_data)} bytes")
        
        # Verify the data structure
        expected_size = 4 + 8 + 8  # u32 + u64 + 8 raw bytes
        if len(chained_data) == expected_size:
            # Parse to verify
            u32_val = struct.unpack('<I', chained_data[0:4])[0]
            u64_val = struct.unpack('<Q', chained_data[4:12])[0]
            raw_bytes = chained_data[12:20]
            
            if u32_val == 100 and u64_val == 200 and raw_bytes == b"\x00" * 8:
                print(f"   ✓ Data correctly serialized")
            else:
                print(f"   ❌ Data mismatch")
                return False
        else:
            print(f"   ❌ Wrong size: expected {expected_size}, got {len(chained_data)}")
            return False
        
        # Test 3: Clear and reuse
        print("\n5. Testing clear() method...")
        builder3 = pyr0.InputBuilder()
        builder3.write_u32(1).write_u32(2)
        
        size_before = builder3.size
        print(f"   Size before clear: {size_before} bytes")
        
        builder3.clear()
        size_after = builder3.size
        print(f"   Size after clear: {size_after} bytes")
        
        if size_after == 0:
            print(f"   ✓ Clear() works correctly")
        else:
            print(f"   ❌ Clear() failed")
            return False
        
        # Reuse after clear
        builder3.write_u64(999)
        final_data = builder3.build()
        if len(final_data) == 8:
            print(f"   ✓ Builder reusable after clear")
        else:
            print(f"   ❌ Builder not properly reusable")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_input_builder_with_prove():
    """Test that InputBuilder works with different prove functions."""
    print("\nTesting InputBuilder with prove variants")
    print("=" * 60)
    
    try:
        # Build test guest
        print("\n1. Preparing test guest...")
        guest_dir = Path("test_cbor_guest")
        elf_data = open(pyr0.build_guest(guest_dir), "rb").read()
        image = pyr0.load_image(elf_data)
        
        # Create input with InputBuilder (matching what guest expects)
        print("\n2. Creating input with InputBuilder...")
        builder = pyr0.InputBuilder()
        payload = [2, b"\x01\x02\x03"]  # Guest expects a=2, b=[1,2,3]
        builder.write_cbor(cbor2.dumps(payload, canonical=True))
        input_data = builder.build()
        
        # Test with regular prove
        print("\n3. Testing with pyr0.prove()...")
        receipt1 = pyr0.prove(image, input_data)
        print(f"   ✓ Regular prove works")
        
        # Test with prove_with_opts
        print("\n4. Testing with pyr0.prove_with_opts()...")
        receipt2 = pyr0.prove_with_opts(image, input_data, succinct=False)
        print(f"   ✓ prove_with_opts works")
        
        # Test with prove_succinct
        print("\n5. Testing with pyr0.prove_succinct()...")
        receipt3 = pyr0.prove_succinct(image, input_data)
        print(f"   ✓ prove_succinct works")
        print(f"   Receipt kind: {receipt3.kind}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run InputBuilder tests."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 17 + "InputBuilder Test Suite" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    
    test1_passed = test_input_builder_standalone()
    test2_passed = test_input_builder_with_prove()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("✅ All InputBuilder tests passed!")
        print("\nInputBuilder provides a general-purpose API for:")
        print("• Constructing guest input data")
        print("• CBOR serialization for complex structures")
        print("• Primitive serialization (u32, u64)")
        print("• Raw byte control when needed")
        print("• Method chaining for cleaner code")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())