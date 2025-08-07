#!/usr/bin/env python3
"""
Example showing how to generate and verify zero-knowledge proofs
with the updated r0prover-python library.
"""

import pyr0
import sys
import time

def main():
    # Step 1: Generate a proof (prover side)
    print("=== PROVER SIDE ===")
    
    # Load the program
    with open("../test/ed25519_verifier.elf", "rb") as f:
        elf_data = f.read()
    image = pyr0.load_image_from_elf(elf_data)
    
    # Create input for Ed25519 verification
    # Using test vector from RFC 8032
    input_data = bytearray()
    # Public key (32 bytes)
    input_data.extend(bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"))
    # Message length (empty message)
    input_data.extend((0).to_bytes(4, 'little'))
    # Signature (64 bytes) 
    input_data.extend(bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"))
    
    # Execute in zkVM
    print("Executing Ed25519 verification in zkVM...")
    segments, info = pyr0.execute_with_input(image, bytes(input_data))
    
    # Generate proof
    print("Generating zero-knowledge proof...")
    start = time.time()
    receipt = pyr0.prove_segment(segments[0])
    end = time.time()
    print(f"Proof generated in {end - start:.2f} seconds")
    
    # Extract journal (public outputs)
    journal = receipt.journal_bytes()
    print(f"Journal (public output): {journal.hex()}")
    print(f"Signature was: {'valid' if journal[0] else 'invalid'}")
    
    # Serialize the receipt (this is what you'd send to verifier)
    print("\nSerializing receipt for transmission...")
    receipt_data = receipt.__getstate__()
    print(f"Serialized receipt size: {len(receipt_data)} bytes")
    
    print("\n" + "="*50 + "\n")
    
    # Step 2: Verify the proof (verifier side)
    print("=== VERIFIER SIDE ===")
    
    # Deserialize the receipt (as if received from prover)
    print("Deserializing receipt...")
    new_receipt = pyr0.SegmentReceipt()
    new_receipt.__setstate__(receipt_data)
    
    # Verify the proof
    print("Verifying the zero-knowledge proof...")
    start = time.time()
    
    # Method 1: Using the receipt's verify method
    is_valid = new_receipt.verify()
    end = time.time()
    print(f"Receipt.verify() returned: {is_valid} in {end - start:.4f} seconds")
    
    # Method 2: Using the standalone function
    start = time.time()
    is_valid2 = pyr0.verify_receipt(new_receipt)
    end = time.time()
    print(f"verify_receipt() returned: {is_valid2} in {end - start:.4f} seconds")
    
    # Extract and check journal from verified receipt
    verified_journal = new_receipt.journal_bytes()
    print(f"\nVerified journal: {verified_journal.hex()}")
    print(f"Signature verification result: {'valid' if verified_journal[0] else 'invalid'}")
    
    if is_valid and is_valid2:
        print("\n✅ SUCCESS: The proof is valid!")
        print("The verifier now knows that:")
        print("- The prover knows a valid Ed25519 signature")
        print("- The signature verification was executed correctly")
        print("- Without seeing the actual signature or message!")
    else:
        print("\n❌ FAILURE: The proof is invalid!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())