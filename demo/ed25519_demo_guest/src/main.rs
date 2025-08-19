use risc0_zkvm::guest::env;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};

fn main() {
    // Read input from host - env::read() will panic if deserialization fails
    let public_key_vec: Vec<u8> = env::read();
    let signature_vec: Vec<u8> = env::read();
    let message: Vec<u8> = env::read();
    
    // Validate input sizes
    if public_key_vec.len() != 32 || signature_vec.len() != 64 {
        // Commit error status and reason
        env::commit(&0u8);  // 0 = invalid
        env::commit(&1u8);  // reason: 1 = size error
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
            // Commit error status and reason
            env::commit(&0u8);  // 0 = invalid
            env::commit(&2u8);  // reason: 2 = invalid public key
            return;
        }
    };
    
    // Create signature
    let signature = Signature::from_bytes(&signature_bytes);
    
    // Verify signature
    let result = verifying_key.verify(&message, &signature);
    
    // Commit result
    if result.is_ok() {
        env::commit(&1u8);  // 1 = valid signature
        env::commit(&public_key_bytes.to_vec());  // Include public key in journal
    } else {
        env::commit(&0u8);  // 0 = invalid signature
        env::commit(&3u8);  // reason: 3 = signature verification failed
    }
}