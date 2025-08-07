#!/usr/bin/env python3
"""
Minimal test of proof verification functionality.
Uses the existing test ELF to verify the API works.
"""

import pyr0
import os

def test_verify_api():
    print("Testing verification API...")
    
    # Use the test ELF
    with open("elf", "rb") as f:
        elf_data = f.read()
    
    # Load and execute
    image = pyr0.load_image_from_elf(elf_data)
    segments, info = pyr0.execute_with_input(image, b"test input")
    
    # Generate proof
    print("Generating proof...")
    receipt = pyr0.prove_segment(segments[0])
    
    # Test journal extraction
    try:
        journal = receipt.journal_bytes()
        print(f"✓ journal_bytes() works: {len(journal)} bytes")
    except Exception as e:
        print(f"✗ journal_bytes() failed: {e}")
        return False
    
    # Test verification
    try:
        is_valid = receipt.verify()
        print(f"✓ receipt.verify() works: {is_valid}")
    except Exception as e:
        print(f"✗ receipt.verify() failed: {e}")
        return False
    
    # Test standalone verification
    try:
        is_valid2 = pyr0.verify_receipt(receipt)
        print(f"✓ verify_receipt() works: {is_valid2}")
    except Exception as e:
        print(f"✗ verify_receipt() failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = test_verify_api()
    sys.exit(0 if success else 1)