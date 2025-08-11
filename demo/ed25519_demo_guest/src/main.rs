use risc0_zkvm::guest::env;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};

fn main() {
    // Start with a debug marker
    env::commit(&99u8);
    
    // Read input from host - env::read() will panic if deserialization fails
    let public_key_vec: Vec<u8> = env::read();
    let signature_vec: Vec<u8> = env::read();
    let message: Vec<u8> = env::read();
    
    // Debug: commit sizes
    env::commit(&(public_key_vec.len() as u8));
    env::commit(&(signature_vec.len() as u8));
    env::commit(&(message.len() as u8));
    
    // Check sizes before proceeding
    if public_key_vec.len() != 32 || signature_vec.len() != 64 {
        env::commit(&200u8); // Error marker
        return;
    }
    
    // Convert to arrays
    let mut public_key_bytes = [0u8; 32];
    public_key_bytes.copy_from_slice(&public_key_vec);
    
    let mut signature_bytes = [0u8; 64];
    signature_bytes.copy_from_slice(&signature_vec);
    
    // Create verifying key
    let verifying_key = match VerifyingKey::from_bytes(&public_key_bytes) {
        Ok(key) => key,
        Err(_) => {
            env::commit(&201u8); // Invalid key marker
            env::commit(&0u8);
            return;
        }
    };
    
    // Create signature
    let signature = Signature::from_bytes(&signature_bytes);
    
    // Verify signature
    let result = verifying_key.verify(&message, &signature);
    
    // Commit result: 1 if valid, 0 if invalid
    if result.is_ok() {
        env::commit(&1u8);
        env::commit(&public_key_bytes.to_vec());
    } else {
        env::commit(&0u8);
    }
}