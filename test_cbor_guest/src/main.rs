use risc0_zkvm::guest::env;
use minicbor::{Decode, Encode};
use std::io::Read;

// Input structure matching Python: {"a": 2, "b": b"\x01\x02\x03"}
// We use numeric field indices for compact CBOR encoding
#[derive(Debug, Decode, Encode)]
struct Input {
    #[n(0)] a: u32,
    #[cbor(n(1), with = "minicbor::bytes")] b: Vec<u8>,
}

// Output structure to prove we correctly decoded the input
#[derive(Debug, Decode, Encode)]
struct Output {
    #[n(0)] sum: u32,  // a + sum of bytes in b
    #[n(1)] a_value: u32,  // echo back the 'a' value
    #[n(2)] b_length: u32,  // length of b array
    #[cbor(n(3), with = "minicbor::bytes")] b_bytes: Vec<u8>,  // echo back b
}

fn main() {
    // Read all input bytes from stdin (raw CBOR bytes)
    let mut buf = Vec::<u8>::new();
    env::stdin().read_to_end(&mut buf).unwrap();
    
    // Decode CBOR to our typed struct
    let input: Input = minicbor::decode(&buf)
        .expect("Failed to decode CBOR input");
    
    // Verify the expected values
    assert_eq!(input.a, 2, "Expected a=2");
    assert_eq!(input.b.len(), 3, "Expected b to have 3 bytes");
    assert_eq!(input.b[0], 0x01, "Expected b[0]=1");
    assert_eq!(input.b[1], 0x02, "Expected b[1]=2");
    assert_eq!(input.b[2], 0x03, "Expected b[2]=3");
    
    // Calculate sum: a + sum(b)
    let sum_bytes: u32 = input.b.iter().map(|&x| x as u32).sum();
    let total = input.a + sum_bytes;  // 2 + (1+2+3) = 8
    
    // Create output that proves we correctly received the data
    let output = Output {
        sum: total,
        a_value: input.a,
        b_length: input.b.len() as u32,
        b_bytes: input.b.clone(),
    };
    
    // Encode output to CBOR and commit to journal
    let out_bytes = minicbor::to_vec(output)
        .expect("Failed to encode output");
    env::commit_slice(&out_bytes);
}