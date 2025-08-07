#!/usr/bin/env python3
"""
Test the verification functionality added to r0prover-python.
"""

import pyr0
import time
import sys
import os

def test_proof_verification():
    """Test generating and verifying a proof"""
    print("=" * 60)
    print("Testing Proof Generation and Verification")
    print("=" * 60)
    
    # Use the Ed25519 verifier ELF if available, or the test ELF
    if os.path.exists("ed25519_verifier.elf"):
        elf_path = "ed25519_verifier.elf"
        # Ed25519 test input (empty message test)
        input_data = bytearray()
        # Public key from RFC 8032 test vector
        input_data.extend(bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"))
        input_data.extend((0).to_bytes(4, 'little'))  # Empty message
        # Signature
        input_data.extend(bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"))
        print("Using Ed25519 verifier ELF")
    else:
        elf_path = "elf"
        input_data = b"Hello, RISC Zero!"
        print("Using test ELF")
    
    # Load the ELF
    print(f"\nLoading ELF from: {elf_path}")
    with open(elf_path, "rb") as f:
        elf_data = f.read()
    image = pyr0.load_image_from_elf(elf_data)
    print(f"✓ ELF loaded ({len(elf_data)} bytes)")
    
    # Execute
    print("\nExecuting in zkVM...")
    tic = time.perf_counter()
    segments, info = pyr0.execute_with_input(image, bytes(input_data))
    toc = time.perf_counter()
    print(f"✓ Execution completed in {toc - tic:.4f} seconds")
    print(f"  Segments: {len(segments)}")
    
    # Generate proof
    print("\nGenerating proof...")
    tic = time.perf_counter()
    receipt = pyr0.prove_segment(segments[0])
    toc = time.perf_counter()
    print(f"✓ Proof generated in {toc - tic:.4f} seconds")
    
    # Check that we have a SegmentReceipt
    print(f"\nReceipt type: {type(receipt)}")
    print(f"Receipt: {receipt}")
    
    # Extract journal
    print("\nExtracting journal (public outputs)...")
    journal = receipt.journal_bytes()
    print(f"✓ Journal extracted: {len(journal)} bytes")
    if len(journal) > 0:
        print(f"  First few bytes: {journal[:min(16, len(journal))].hex()}")
    
    # Verify the proof
    print("\nVerifying the proof...")
    tic = time.perf_counter()
    
    # Test the method on the receipt object
    is_valid = receipt.verify()
    toc = time.perf_counter()
    print(f"✓ Receipt.verify() returned: {is_valid} in {toc - tic:.4f} seconds")
    
    # Test the standalone function
    tic = time.perf_counter()
    is_valid2 = pyr0.verify_receipt(receipt)
    toc = time.perf_counter()
    print(f"✓ verify_receipt() returned: {is_valid2} in {toc - tic:.4f} seconds")
    
    if is_valid and is_valid2:
        print("\n✅ SUCCESS: Proof is valid!")
    else:
        print("\n❌ FAILURE: Proof verification failed!")
        
    return is_valid and is_valid2

if __name__ == "__main__":
    try:
        success = test_proof_verification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)