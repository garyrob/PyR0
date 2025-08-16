#!/usr/bin/env python3
"""
Security test demonstrating the importance of external image ID verification.

SECURITY INVARIANT: Never derive the image ID from the receipt itself during
verification. Always use a trusted, externally-provided image ID.
"""

import sys
import pyr0
from pathlib import Path

print("=== Security Test: Image ID Verification ===\n")

test_passed = True

# Load the test program
test_elf_path = Path("demo/ed25519_demo_guest/target/riscv32im-risc0-zkvm-elf/release/ed25519-guest-input")
if not test_elf_path.exists():
    print("❌ Test ELF not found. Please build the demo first.")
    sys.exit(1)

print("1. Loading legitimate program...")
with open(test_elf_path, "rb") as f:
    elf_data = f.read()

image = pyr0.load_image(elf_data)
trusted_image_id = image.id  # This is our trusted image ID
print(f"   ✓ Loaded program with image ID: {trusted_image_id.hex()[:16]}...")

print("\n2. Generating a valid proof...")
from pyr0 import serialization

# Create valid input
pk_bytes = b'\x00' * 32  
sig_bytes = b'\x00' * 64  
msg_bytes = b''
input_data = serialization.ed25519_input(pk_bytes, sig_bytes, msg_bytes)

receipt = pyr0.prove(image, input_data)
print(f"   ✓ Generated receipt for our program")

print("\n3. Testing verification methods...")

print("\n   a) Using verify() with trusted image ID (SECURE):")
try:
    receipt.verify(trusted_image_id)  # Uses our trusted image ID
    print("      ✓ Verification passed with trusted image ID")
    print("      ✓ This is the secure way to verify!")
except Exception as e:
    print(f"      ✗ Verification failed: {e}")
    test_passed = False

print("\n   b) Testing with wrong image ID (should fail):")
wrong_image_id = b'\xFF' * 32  # Obviously wrong image ID
try:
    receipt.verify(wrong_image_id)
    print("      ❌ ERROR: Verification should have failed with wrong image ID!")
    test_passed = False
except Exception as e:
    print(f"      ✓ Correctly rejected wrong image ID: {e}")

print("\n=== Security Recommendation ===")
print("ALWAYS pass a trusted image ID to verify():")
print("  - From Image.id after loading a trusted ELF")
print("  - From a compile-time constant (e.g., PROGRAM_ID)")  
print("  - From compute_image_id() on a locally known ELF")
print("  - From a secure configuration/database")
print("\nNEVER derive the image ID from the receipt being verified!")

# Exit with appropriate code
if test_passed:
    print("\n✓ All security tests passed")
    sys.exit(0)
else:
    print("\n✗ Some security tests failed")
    sys.exit(1)