// Example RISC Zero guest program for Ed25519 signature verification
// This file shows what needs to be compiled to create ed25519_verifier.elf
//
// Based on: https://github.com/jeswr/risc0-ed25519-zk-sparql
//
// To compile this:
// 1. Create a new RISC Zero project: `cargo risczero new ed25519-verifier`
// 2. Replace the guest/src/main.rs with this code
// 3. Add ed25519-dalek to guest/Cargo.toml
// 4. Build with: `cargo risczero build`
// 5. Copy the resulting ELF to test/ed25519_verifier.elf

#![no_main]
#![no_std]

use risc0_zkvm::guest::env;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};

risc0_zkvm::guest::entry!(main);

fn main() {
    // Read the public key from the host (32 bytes)
    let public_key_bytes: [u8; 32] = env::read();
    
    // Read the message length
    let message_len: u32 = env::read();
    
    // Read the message
    let message = if message_len > 0 {
        let mut msg = vec![0u8; message_len as usize];
        env::read_slice(&mut msg);
        msg
    } else {
        vec![]
    };
    
    // Read the signature from the host (64 bytes)
    let signature_bytes: [u8; 64] = env::read();
    
    // Parse the public key
    let verifying_key = match VerifyingKey::from_bytes(&public_key_bytes) {
        Ok(key) => key,
        Err(_) => {
            // Invalid public key
            env::commit(&false);
            return;
        }
    };
    
    // Parse the signature
    let signature = match Signature::from_bytes(&signature_bytes) {
        Ok(sig) => sig,
        Err(_) => {
            // Invalid signature format
            env::commit(&false);
            return;
        }
    };
    
    // Verify the signature
    let is_valid = verifying_key.verify(&message, &signature).is_ok();
    
    // Commit the verification result
    // This proves that we know a valid signature without revealing it
    env::commit(&is_valid);
    
    // Optionally, we could also commit a hash of the message or other metadata
    // to prove additional properties about what was signed
    if is_valid {
        // Could add additional commitments here
        // For example, committing a hash of the message:
        // use sha2::{Sha256, Digest};
        // let mut hasher = Sha256::new();
        // hasher.update(&message);
        // let message_hash = hasher.finalize();
        // env::commit(&message_hash);
    }
}

// Alternative implementation with more detailed error handling:
#[allow(dead_code)]
fn main_with_detailed_errors() {
    #[derive(Debug, Clone, Copy)]
    #[repr(u8)]
    enum VerificationResult {
        Valid = 0,
        InvalidPublicKey = 1,
        InvalidSignature = 2,
        VerificationFailed = 3,
    }
    
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
    
    let result = match VerifyingKey::from_bytes(&public_key_bytes) {
        Ok(verifying_key) => {
            match Signature::from_bytes(&signature_bytes) {
                Ok(signature) => {
                    if verifying_key.verify(&message, &signature).is_ok() {
                        VerificationResult::Valid
                    } else {
                        VerificationResult::VerificationFailed
                    }
                }
                Err(_) => VerificationResult::InvalidSignature,
            }
        }
        Err(_) => VerificationResult::InvalidPublicKey,
    };
    
    env::commit(&(result as u8));
}