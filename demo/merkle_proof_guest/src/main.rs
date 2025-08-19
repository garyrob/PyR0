// RISC Zero zkVM guest program for Merkle tree membership proofs
// Equivalent to the Noir 2LA circuit functionality

#![no_main]
#![no_std]

extern crate alloc;
use alloc::vec;
use alloc::vec::Vec;

use risc0_zkvm::guest::env;
use borsh::BorshSerialize;
use sha2::{Sha256, Digest};

// Output structure - using Borsh for cross-language compatibility
#[derive(BorshSerialize)]
struct MerkleProofOutput {
    root: [u8; 32],       // Computed Merkle root
    k_pub: [u8; 32],      // Public key (optionally exposed)
}

// Simple hash function for combining two nodes
// In production, this should use Poseidon hash for efficiency
fn hash_nodes(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(left);
    hasher.update(right);
    let result = hasher.finalize();
    let mut output = [0u8; 32];
    output.copy_from_slice(&result);
    output
}

// Compute leaf commitment C = Hash(k_pub || r || e)
fn compute_leaf(k_pub: &[u8; 32], r: &[u8; 32], e: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(k_pub);
    hasher.update(r);
    hasher.update(e);
    let result = hasher.finalize();
    let mut output = [0u8; 32];
    output.copy_from_slice(&result);
    output
}

// Verify Merkle path and compute root
fn verify_merkle_path(
    leaf: [u8; 32],
    path: &[[u8; 32]],
    indices: &[bool],
) -> [u8; 32] {
    assert_eq!(path.len(), indices.len(), "Path and indices length mismatch");
    
    let mut current = leaf;
    
    // Traverse from leaf to root
    for (sibling, is_right) in path.iter().zip(indices.iter()) {
        current = if *is_right {
            // Current node is on the right, sibling on the left
            hash_nodes(sibling, &current)
        } else {
            // Current node is on the left, sibling on the right
            hash_nodes(&current, sibling)
        };
    }
    
    current
}

risc0_zkvm::guest::entry!(main);

fn main() {
    // Use env::read_slice() for efficient byte reading
    // Python sends raw bytes, no u32 expansion
    
    // Read all input at once into a buffer
    // We know the exact size: 32*3 + 32*16 + 16 = 96 + 512 + 16 = 624 bytes
    let mut input_buffer = vec![0u8; 624];
    env::read_slice(&mut input_buffer);
    
    // Create a cursor to read from the buffer
    let mut offset = 0;
    
    // Read k_pub (32 bytes)
    let mut k_pub = [0u8; 32];
    k_pub.copy_from_slice(&input_buffer[offset..offset+32]);
    offset += 32;
    
    // Read r (32 bytes)
    let mut r = [0u8; 32];
    r.copy_from_slice(&input_buffer[offset..offset+32]);
    offset += 32;
    
    // Read e (32 bytes)
    let mut e = [0u8; 32];
    e.copy_from_slice(&input_buffer[offset..offset+32]);
    offset += 32;
    
    // Read path length (16 for our fixed-depth tree)
    // For simplicity, we'll hardcode 16 levels since that's what we always use
    let path_len = 16usize;
    
    // Read path siblings (16 * 32 bytes)
    let mut path = Vec::new();
    for _ in 0..path_len {
        let mut sibling = [0u8; 32];
        sibling.copy_from_slice(&input_buffer[offset..offset+32]);
        offset += 32;
        path.push(sibling);
    }
    
    // Read indices (16 bytes, one per level)
    let mut indices = Vec::new();
    for _ in 0..path_len {
        indices.push(input_buffer[offset] != 0);
        offset += 1;
    }
    
    // Step 1: Compute the leaf commitment C = Hash(k_pub || r || e)
    let leaf = compute_leaf(&k_pub, &r, &e);
    
    // Step 2: Verify the Merkle path and compute the root
    let computed_root = verify_merkle_path(leaf, &path, &indices);
    
    // Step 3: Create output with public values
    let output = MerkleProofOutput {
        root: computed_root,
        k_pub: k_pub,  // Optionally expose k_pub as public
    };
    
    // Serialize with Borsh and commit as raw bytes
    let bytes = borsh::to_vec(&output).unwrap();
    env::commit_slice(&bytes);
}

