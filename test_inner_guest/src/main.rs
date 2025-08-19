
use risc0_zkvm::guest::env;

fn main() {
    // Read two numbers
    let a: u32 = env::read();
    let b: u32 = env::read();
    
    // Compute sum
    let sum = a + b;
    
    // Commit the sum to the journal
    env::commit(&sum);
}
