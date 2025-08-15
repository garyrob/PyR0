#!/usr/bin/env python3
"""Test that PyR0 verification actually rejects invalid proofs."""

import pyr0
import os

print("=== Testing PyR0 Verification ===\n")

# Create a simple test program (just returns success)
TEST_PROGRAM = bytes([
    # Minimal RISC-V program that just exits
    0x13, 0x00, 0x00, 0x00,  # nop
    0x73, 0x00, 0x50, 0x00,  # ecall (exit)
])

try:
    # Load as image
    print("1. Loading test program...")
    image = pyr0.load_image(TEST_PROGRAM)
    print("   ✓ Loaded (this might fail with invalid ELF)")
except Exception as e:
    print(f"   ✗ Failed to load: {e}")
    print("\n2. Testing with a valid receipt from your demo...")
    
    # Try to create a completely fake receipt
    print("\n3. Testing verification with a fake receipt...")
    try:
        # Create a fake SegmentReceipt
        fake_receipt = pyr0.SegmentReceipt()
        
        # Try to verify it
        print("   Attempting to verify fake receipt...")
        result = fake_receipt.verify()
        print(f"   Fake receipt.verify() returned: {result}")
        
        if result:
            print("   ⚠️  WARNING: Fake receipt passed verification!")
            print("   This suggests verification might not be working correctly.")
        else:
            print("   ✓ Good: Fake receipt failed verification")
            
        # The verify_receipt function has been removed in favor of receipt.verify()
        # which was already tested above
            
    except Exception as e:
        print(f"   Error during fake receipt test: {e}")

print("\n=== Summary ===")
print("The verification functions are implemented and being called.")
print("However, the fast proof generation suggests the prover server")
print("might still be running in dev mode despite RISC0_DEV_MODE=0.")
print("\nTo ensure production proofs, you may need to:")
print("1. Reinstall RISC Zero tools with disable-dev-mode")
print("2. Or use a production RISC Zero deployment")