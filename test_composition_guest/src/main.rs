// Test guest for proof composition
// This guest verifies an inner proof and adds its own computation

use risc0_zkvm::guest::env;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Receipt {
    journal: Journal,
    // Other fields we don't need to deserialize
}

#[derive(Serialize, Deserialize)]
struct Journal {
    bytes: Vec<u8>,
}

fn main() {
    // Read the composition input (from composition_input() helper)
    let receipt_bytes: Vec<u8> = env::read();
    let expected_image_id_vec: Vec<u8> = env::read();
    let additional_data: Vec<u8> = env::read();
    
    // Convert image ID from Vec to fixed array
    if expected_image_id_vec.len() != 32 {
        panic!("Image ID must be 32 bytes");
    }
    let mut expected_image_id = [0u8; 32];
    expected_image_id.copy_from_slice(&expected_image_id_vec);
    
    // Verify the inner proof
    env::verify(expected_image_id, &receipt_bytes).unwrap();
    
    // Extract the journal from the verified receipt
    let receipt: Receipt = bincode::deserialize(&receipt_bytes).unwrap();
    let inner_journal = receipt.journal.bytes;
    
    // The inner journal should have the Ed25519 verification result
    // First byte is marker (99), then sizes, then at position 16 is the result
    let verification_result = if inner_journal.len() > 16 {
        inner_journal[16]
    } else {
        0
    };
    
    // Commit our own output showing we verified the inner proof
    env::commit(&42u8);  // Marker that we're the outer program
    env::commit(&verification_result);  // Pass through the inner result
    env::commit(&(inner_journal.len() as u32));  // Size of inner journal
    env::commit(&(additional_data.len() as u32));  // Size of additional data
}