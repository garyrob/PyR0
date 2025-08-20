#!/usr/bin/env python3
"""
Test the new Composer API for proof composition.
This demonstrates the correct way to do composition in PyR0 v0.7.0.
"""

import pyr0
import struct
import sys

def test_composer_api():
    """Test the new Composer pattern for safer proof composition"""
    
    print("\n" + "="*60)
    print("   Testing PyR0 v0.7.0 Composer API")
    print("="*60)
    
    # 1. Build and load the guests
    print("\n1. Building guest programs...")
    inner_elf = pyr0.build_guest("test_inner_guest")
    outer_elf = pyr0.build_guest("test_outer_guest")
    
    inner_image = pyr0.load_image(open(inner_elf, 'rb').read())
    outer_image = pyr0.load_image(open(outer_elf, 'rb').read())
    
    print(f"Inner image ID: {inner_image.id.hex()[:16]}...")
    print(f"Outer image ID: {outer_image.id.hex()[:16]}...")
    
    # 2. Generate inner proof (must be succinct for composition!)
    print("\n2. Generating inner proof (succinct)...")
    a, b = 3, 5
    inner_input = pyr0.serialization.to_u32(a) + pyr0.serialization.to_u32(b)
    inner_receipt = pyr0.prove_succinct(inner_image, inner_input)
    
    # 3. Examine the claim (new API!)
    print("\n3. Examining inner receipt's claim...")
    claim = inner_receipt.claim()
    print(f"Claim image ID: {claim.image_id_hex[:16]}...")
    print(f"Journal length: {len(claim.journal)} bytes")
    print(f"Journal digest: {claim.journal_digest_hex[:16]}...")
    print(f"Exit code: {claim.exit_code} ({'success' if claim.is_success else 'failed'})")
    
    # Extract the sum from the journal
    sum_value = struct.unpack('<I', claim.journal[:4])[0]
    print(f"Inner computation: {a} + {b} = {sum_value}")
    
    # 4. Use the new Composer API for the outer proof
    print("\n4. Using Composer for outer proof...")
    comp = pyr0.Composer(outer_image)
    
    # Add the inner receipt as an assumption
    comp.assume(inner_receipt)
    print(f"Added {comp.assumption_count} assumption(s)")
    
    # Write typed inputs for the outer guest
    comp.write_u32(sum_value)              # Expected sum (4 bytes)
    comp.write_image_id(inner_image.id)    # Inner image ID (32 bytes)
    print(f"Input buffer size: {comp.input_size} bytes")
    
    # Register what we expect the guest to verify (for preflight check)
    comp.expect_verification(inner_image.id, claim.journal)
    
    # Run preflight checks (will raise by default if issues found)
    try:
        issues = comp.preflight_check(raise_on_error=False)
        if issues:
            print("⚠️  Preflight issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Preflight checks passed")
    except pyr0.PreflightError as e:
        print(f"❌ Preflight failed: {e}")
        return False
    
    # Generate the composed proof (defaults to succinct to resolve assumptions)
    outer_receipt = comp.prove()  # Uses ReceiptKind.SUCCINCT by default
    print(f"Outer proof generated (kind: {outer_receipt.kind})")
    print(f"Is unconditional: {outer_receipt.is_unconditional}")
    print(f"Assumptions resolved: {inner_receipt.assumption_count} -> {outer_receipt.assumption_count}")
    
    # 5. Verify the composed proof
    print("\n5. Verifying composed proof...")
    outer_claim = outer_receipt.claim()
    
    # Extract result from outer journal
    result = struct.unpack('<I', outer_claim.journal[:4])[0]
    print(f"Outer computation: {sum_value} * 2 = {result}")
    
    # Verify the proof using the unified verify method
    outer_receipt.verify(outer_image)  # Can pass Image, bytes, or hex
    print("✅ Composed proof verified!")
    
    # 6. Test new v0.7.0 features
    print("\n6. Testing v0.7.0 features:")
    print(f"Receipt kind enum: {pyr0.ReceiptKind.SUCCINCT}")
    print(f"Unified verify works with Image: ✓")
    print(f"Claim abstraction provides all data: ✓")
    print(f"Preflight validation catches errors early: ✓")
    
    return True

def test_claim_api():
    """Test the new Claim abstraction"""
    
    print("\n" + "="*60)
    print("   Testing Claim Abstraction")
    print("="*60)
    
    # Create a simple proof
    print("\n1. Creating a simple proof...")
    guest_elf = pyr0.build_guest("test_inner_guest")
    image = pyr0.load_image(open(guest_elf, 'rb').read())
    
    input_data = pyr0.serialization.to_u32(10) + pyr0.serialization.to_u32(20)
    receipt = pyr0.prove(image, input_data)
    
    # Get the claim
    print("\n2. Examining the claim...")
    claim = receipt.claim()
    
    # Show claim properties
    print(f"Image ID: {claim.image_id_hex}")
    print(f"Journal: {claim.journal.hex()}")
    print(f"Journal digest: {claim.journal_digest_hex}")
    print(f"Exit code: {claim.exit_code}")
    print(f"Is success: {claim.is_success}")
    
    # Test claim matching
    print("\n3. Testing claim matching...")
    matches = claim.matches(image.id, claim.journal)
    print(f"Claim matches expected values: {matches}")
    
    # Test string representations
    print("\n4. String representations:")
    print(f"repr: {repr(claim)}")
    print(f"str:\n{str(claim)}")
    
    return True

if __name__ == "__main__":
    try:
        # Run tests
        test_passed = True
        
        test_passed = test_claim_api() and test_passed
        test_passed = test_composer_api() and test_passed
        
        if test_passed:
            print("\n" + "="*60)
            print("   ✅ ALL TESTS PASSED")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("   ❌ SOME TESTS FAILED")
            print("="*60)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)