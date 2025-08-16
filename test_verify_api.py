#!/usr/bin/env python3
"""Quick test to check if verify() requires image_id parameter."""

import sys
import importlib

test_passed = True

# Force reimport
if 'pyr0' in sys.modules:
    del sys.modules['pyr0']
if 'pyr0._rust' in sys.modules:
    del sys.modules['pyr0._rust']

import pyr0
import inspect

print("Testing Receipt.verify() signature...")
print(f"Signature: {inspect.signature(pyr0._rust.Receipt.verify)}")

# Try to use it
from pathlib import Path

test_elf_path = Path("demo/ed25519_demo_guest/target/riscv32im-risc0-zkvm-elf/release/ed25519-guest-input")
if test_elf_path.exists():
    with open(test_elf_path, "rb") as f:
        elf_data = f.read()
    
    image = pyr0.load_image(elf_data)
    print(f"Loaded image with ID: {image.id.hex()[:16]}...")
    
    # Create a simple proof
    from pyr0 import serialization
    input_data = serialization.ed25519_input(b'\x00' * 32, b'\x00' * 64, b'')
    
    print("Generating proof...")
    receipt = pyr0.prove(image, input_data)
    
    print("\nTrying verify() without image_id (should fail if API is updated)...")
    api_updated = False
    try:
        receipt.verify()
        print("  ✗ verify() worked without image_id - OLD API still in use")
        test_passed = False  # This is a problem - the secure API should be in use
    except TypeError as e:
        print(f"  ✓ verify() requires image_id - NEW API in use: {e}")
        api_updated = True
    
    print("\nTrying verify(image_id)...")
    try:
        receipt.verify(image.id)
        print("  ✓ verify(image_id) worked - NEW API")
        if not api_updated:
            print("  ✗ ERROR: Both old and new API work - unexpected state!")
            test_passed = False
    except Exception as e:
        print(f"  ✗ verify(image_id) failed: {e}")
        if api_updated:
            test_passed = False  # New API should work
else:
    print("✗ Test ELF not found")
    test_passed = False

# Exit with appropriate code
if test_passed:
    print("\n✓ API test passed")
    sys.exit(0)
else:
    print("\n✗ API test failed")
    sys.exit(1)