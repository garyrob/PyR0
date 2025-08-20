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

test_guest_dir = Path("demo/ed25519_demo_guest")
try:
    elf_path = pyr0.build_guest(test_guest_dir, "ed25519-guest-input")
    with open(elf_path, "rb") as f:
        elf_data = f.read()
    
    image = pyr0.load_image(elf_data)
    print(f"Loaded image with ID: {image.id.hex()[:16]}...")
    
    # Create a simple proof
    from pyr0 import serialization
    input_data = serialization.ed25519_input(b'\x00' * 32, b'\x00' * 64, b'')
    
    print("Generating proof...")
    receipt = pyr0.prove(image, input_data)
    
    print("\nTrying verify() without image_id (should fail)...")
    try:
        receipt.verify()
        print("  ❌ verify() worked without image_id - SECURITY ISSUE!")
        test_passed = False
    except TypeError as e:
        print(f"  ✓ verify() requires image_id: {e}")
    
    print("\nTrying polymorphic verify with different types...")
    
    # Test with bytes
    try:
        receipt.verify(image.id)
        print("  ✓ verify(bytes) worked")
    except Exception as e:
        print(f"  ❌ verify(bytes) failed: {e}")
        test_passed = False
    
    # Test with hex string
    try:
        receipt.verify(image.id_hex)
        print("  ✓ verify(hex_string) worked")
    except Exception as e:
        print(f"  ❌ verify(hex_string) failed: {e}")
        test_passed = False
        
    # Test with Image object
    try:
        receipt.verify(image)
        print("  ✓ verify(Image) worked")
    except Exception as e:
        print(f"  ❌ verify(Image) failed: {e}")
        test_passed = False
except (pyr0.GuestBuildFailedError, pyr0.ElfNotFoundError) as e:
    print(f"❌ Could not build test ELF: {e}")
    test_passed = False

# Exit with appropriate code
if test_passed:
    print("\n✓ API test passed")
    sys.exit(0)
else:
    print("\n❌ API test failed")
    sys.exit(1)