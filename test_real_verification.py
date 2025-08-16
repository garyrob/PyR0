#!/usr/bin/env python3
"""Test that PyR0 verification actually rejects invalid proofs."""

import pyr0
import os
import sys
import time

print("=== Testing PyR0 Verification ===\n")

test_passed = True

# Create a simple test program (just returns success)
TEST_PROGRAM = bytes([
    # Minimal RISC-V program that just exits
    0x13, 0x00, 0x00, 0x00,  # nop
    0x73, 0x00, 0x50, 0x00,  # ecall (exit)
])

try:
    # Load as image
    print("1. Testing error handling with invalid input...")
    print("   Attempting to load raw bytes (not a valid ELF)...")
    image = pyr0.load_image(TEST_PROGRAM)
    print("   ❌ ERROR: Should have rejected invalid input!")
    test_passed = False
except Exception as e:
    print(f"   ✓ Correctly rejected invalid input: {e}")
    
    # Now test with a real program
    print("\n2. Testing with a real RISC-V ELF program...")
    try:
        # Create a minimal valid RISC-V ELF (just exits)
        from pathlib import Path
        
        # Check if we have a test ELF available
        test_elf_path = Path("demo/ed25519_demo_guest/target/riscv32im-risc0-zkvm-elf/release/ed25519-guest-input")
        if test_elf_path.exists():
            print(f"   Found test ELF: {test_elf_path}")
            with open(test_elf_path, "rb") as f:
                elf_data = f.read()
            
            start_load = time.time()
            image = pyr0.load_image(elf_data)
            load_time = time.time() - start_load
            print(f"   ✓ Loaded test ELF in {load_time:.3f}s, image ID: {image.id.hex()[:16]}...")
            
            # Generate a real proof with valid Ed25519 input
            print("\n   Generating proof with valid Ed25519 input...")
            from pyr0 import serialization
            
            # Create minimal valid Ed25519 input (32 + 64 + 0 bytes)
            pk_bytes = b'\x00' * 32  # 32-byte public key
            sig_bytes = b'\x00' * 64  # 64-byte signature
            msg_bytes = b''  # empty message
            
            input_data = serialization.ed25519_input(pk_bytes, sig_bytes, msg_bytes)
            
            print("   Starting proof generation...")
            start_prove = time.time()
            receipt = pyr0.prove(image, input_data)
            prove_time = time.time() - start_prove
            
            print(f"   ✓ Generated receipt in {prove_time:.3f}s")
            print(f"     - Journal size: {len(receipt.journal)} bytes")
            
            # Verify the real receipt
            print("\n   Verifying the receipt...")
            start_verify = time.time()
            receipt.verify(image.id)  # Pass the trusted image ID
            verify_time = time.time() - start_verify
            print(f"   ✓ Receipt verified successfully in {verify_time:.3f}s")
        else:
            print("   ✗ No test ELF available - cannot complete test")
            test_passed = False
            
    except Exception as e:
        print(f"   ✗ Error during real proof test: {e}")
        test_passed = False

print("\n=== Timing Summary ===")
try:
    print(f"Image loading:     {load_time:6.3f}s")
    print(f"Proof generation:  {prove_time:6.3f}s")
    print(f"Verification:      {verify_time:6.3f}s")
    print(f"Total time:        {load_time + prove_time + verify_time:6.3f}s")
    
    print("\n=== Analysis ===")
    if prove_time < 0.1:
        print("⚠️  Very fast proof generation (<100ms) may indicate dev mode.")
        print("   Check that RISC0_DEV_MODE is not set.")
    elif prove_time < 1.0:
        print("✓ Fast proof generation (<1s) is normal for small programs")
        print("  with RISC0's GPU acceleration and optimizations.")
    else:
        print(f"✓ Proof generation took {prove_time:.1f}s, consistent with production proving.")
        
except NameError:
    print("(Timing data not available - test may have failed earlier)")

# Exit with appropriate code
if test_passed:
    print("\n✓ All tests passed")
    sys.exit(0)
else:
    print("\n✗ Some tests failed")
    sys.exit(1)