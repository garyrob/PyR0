// RISC Zero zkVM guest program for Merkle tree membership proofs
// Equivalent to the Noir 2LA circuit functionality

#![no_main]
#![no_std]

extern crate alloc;
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
    // RISC Zero serializes everything through env::read()
    // Each byte becomes a u32 in the input stream
    
    // Read k_pub (32 bytes, each as u32)
    let mut k_pub = [0u8; 32];
    for i in 0..32 {
        k_pub[i] = env::read::<u32>() as u8;
    }
    
    // Read r (32 bytes, each as u32)
    let mut r = [0u8; 32];
    for i in 0..32 {
        r[i] = env::read::<u32>() as u8;
    }
    
    // Read e (32 bytes, each as u32)
    let mut e = [0u8; 32];
    for i in 0..32 {
        e[i] = env::read::<u32>() as u8;
    }
    
    // Read path length
    let path_len: u32 = env::read();
    assert_eq!(path_len, 16, "Merkle path must have 16 levels");
    
    // Read path siblings (each is 32 bytes)
    let mut path = Vec::new();
    for _ in 0..path_len {
        let mut sibling = [0u8; 32];
        for j in 0..32 {
            sibling[j] = env::read::<u32>() as u8;
        }
        path.push(sibling);
    }
    
    // Read indices length
    let indices_len: u32 = env::read();
    assert_eq!(indices_len, 16, "Must have 16 index bits");
    
    // Read indices (each byte as u32)
    let mut indices = Vec::new();
    for _ in 0..indices_len {
        let bit_val: u32 = env::read();
        indices.push(bit_val != 0);
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

// Alternative version that uses Poseidon hash (placeholder for now)
// In production, we'd import a Poseidon implementation optimized for zkVM
#[allow(dead_code)]
fn poseidon_hash(_inputs: &[[u8; 32]]) -> [u8; 32] {
    // Placeholder - would use actual Poseidon implementation
    // For now, using SHA256 as fallback
    let mut hasher = Sha256::new();
    for input in _inputs {
        hasher.update(input);
    }
    let result = hasher.finalize();
    let mut output = [0u8; 32];
    output.copy_from_slice(&result);
    output
}