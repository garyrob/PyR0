
use risc0_zkvm::guest::env;

fn main() {
    // Read the expected sum from the Composer's write_u32 (4 bytes)
    let mut sum_bytes = [0u8; 4];
    env::read_slice(&mut sum_bytes);
    let expected_sum = u32::from_le_bytes(sum_bytes);
    
    // Read the image ID from the Composer's write_image_id (32 bytes)
    let mut inner_image_id = [0u8; 32];
    env::read_slice(&mut inner_image_id);
    
    // Create expected journal (inner guest commits a u32)
    let expected_journal = risc0_zkvm::serde::to_vec(&expected_sum).unwrap();
    
    // Verify the assumption (inner proof)
    // This will be checked when the outer proof is verified
    env::verify(inner_image_id, &expected_journal).unwrap();
    
    // Do some additional computation with the verified sum
    let result = expected_sum * 2;
    
    // Commit the result
    env::commit(&result);
}
