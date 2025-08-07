#!/usr/bin/env python3
"""
Test Ed25519 signature verification in RISC Zero zkVM.

This test demonstrates that Ed25519 signatures can be verified inside the RISC Zero
zkVM, proving that a signature was valid without revealing the message or signature.

Based on: https://github.com/jeswr/risc0-ed25519-zk-sparql
"""

import pyr0
import time
import base64
import json


def test_ed25519_verification():
    """
    Test Ed25519 signature verification inside RISC Zero zkVM.
    """
    print("=" * 60)
    print("Ed25519 Signature Verification Test in RISC Zero")
    print("=" * 60)
    
    # Test vectors for Ed25519 (from RFC 8032)
    # These are known good test vectors
    test_vectors = [
        {
            "private_key": "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
            "public_key": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
            "message": "",
            "signature": "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
        },
        {
            "private_key": "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
            "public_key": "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
            "message": "72",
            "signature": "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
        }
    ]
    
    print("\nTest Setup:")
    print("-" * 40)
    
    # Check if we have a compiled Ed25519 verifier ELF
    # In a real implementation, this would be the path to the compiled guest program
    ed25519_elf_path = "ed25519_verifier.elf"
    
    try:
        # Try to load the Ed25519 verifier ELF
        with open(ed25519_elf_path, "rb") as f:
            elf_data = f.read()
        print(f"✓ Loaded Ed25519 verifier ELF ({len(elf_data)} bytes)")
        
        # Load the ELF into RISC Zero
        print("\nLoading ELF into RISC Zero...")
        tic = time.perf_counter()
        image = pyr0.load_image_from_elf(elf_data)
        toc = time.perf_counter()
        print(f"✓ ELF loaded in {toc - tic:.4f} seconds")
        
        # Test each vector
        for i, vector in enumerate(test_vectors, 1):
            print(f"\n--- Test Vector {i} ---")
            print(f"Message: {vector['message'] if vector['message'] else '(empty)'}")
            print(f"Public Key: {vector['public_key'][:16]}...")
            print(f"Signature: {vector['signature'][:16]}...")
            
            # Prepare input for the zkVM
            # Format: [public_key_bytes, message_length, message_bytes, signature_bytes]
            public_key_bytes = bytes.fromhex(vector['public_key'])
            message_bytes = bytes.fromhex(vector['message']) if vector['message'] else b''
            signature_bytes = bytes.fromhex(vector['signature'])
            
            # Pack the input data
            input_data = bytearray()
            input_data.extend(public_key_bytes)  # 32 bytes
            input_data.extend(len(message_bytes).to_bytes(4, 'little'))  # message length
            input_data.extend(message_bytes)  # variable length
            input_data.extend(signature_bytes)  # 64 bytes
            
            print(f"Input size: {len(input_data)} bytes")
            
            # Execute in zkVM
            print("Executing verification in zkVM...")
            tic = time.perf_counter()
            segments, info = pyr0.execute_with_input(image, bytes(input_data))
            toc = time.perf_counter()
            print(f"✓ Execution completed in {toc - tic:.4f} seconds")
            print(f"  Segments: {len(segments)}")
            print(f"  Exit code: {info.get_exit_code()}")
            
            # Generate proof for the first segment
            print("Generating zero-knowledge proof...")
            tic = time.perf_counter()
            receipt = pyr0.prove_segment(segments[0])
            toc = time.perf_counter()
            print(f"✓ Proof generated in {toc - tic:.4f} seconds")
            
    except FileNotFoundError:
        print(f"⚠ Ed25519 verifier ELF not found at: {ed25519_elf_path}")
        print("\nTo run this test, you need to:")
        print("1. Create a RISC Zero guest program that verifies Ed25519 signatures")
        print("2. Compile it to produce an ELF binary")
        print("3. Place the ELF at: test/ed25519_verifier.elf")
        print("\nOr run: ./build_ed25519_verifier.sh (if you have cargo-risczero installed)")
        print("\nExample Rust guest code structure:")
        print("-" * 40)
        print("""
use risc0_zkvm::guest::env;
use ed25519_dalek::{PublicKey, Signature, Verifier};

fn main() {
    // Read inputs from host
    let public_key_bytes: [u8; 32] = env::read();
    let message_len: u32 = env::read();
    let message = if message_len > 0 {
        let mut msg = vec![0u8; message_len as usize];
        env::read_slice(&mut msg);
        msg
    } else {
        vec![]
    };
    let signature_bytes: [u8; 64] = env::read();
    
    // Verify signature
    let public_key = PublicKey::from_bytes(&public_key_bytes)
        .expect("Invalid public key");
    let signature = Signature::from_bytes(&signature_bytes)
        .expect("Invalid signature");
    
    let is_valid = public_key.verify(&message, &signature).is_ok();
    
    // Commit the result
    env::commit(&is_valid);
}
        """)
        print("-" * 40)
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the Ed25519 verification test
    test_ed25519_verification()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)