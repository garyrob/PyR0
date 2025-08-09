//! Sparse-Merkle wrapper around the `sparse-merkle-tree` crate.
//!
//! This wrapper uses a Poseidon-over-BN254 hasher to provide Merkle proofs 
//! compatible with zero-knowledge circuits.

use sparse_merkle_tree::merkle_proof::CompiledMerkleProof;
use sparse_merkle_tree::{default_store::DefaultStore, SparseMerkleTree, H256};
use sparse_merkle_tree::traits::Value;
use std::convert::TryInto;

use num_bigint::BigUint;
use poseidon_bn128::poseidon;
use scalarff::Bn128FieldElement;
use scalarff::FieldElement;

// ---------------------------------------------------------------------------
// Constant-value leaf (`1`) – zero-sized, hashes to 0x…01
// ---------------------------------------------------------------------------

/// Zero-sized marker value representing the constant leaf `1`.
#[derive(Clone, Copy, Default)]
pub struct One;

impl Value for One {
    fn to_h256(&self) -> H256 {
        let mut bytes = [0u8; 32];
        bytes[31] = 1; // big-endian 1
        bytes.into()
    }

    fn zero() -> Self {
        One
    }
}

/// Convenience helpers for converting between hex strings and the `H256`
/// wrapper type used by the SMT crate.
pub fn hex_to_h256(s: &str) -> Result<H256, String> {
    // Detect if the string is pure decimal (\d+) – in that case treat it as a
    // decimal encoding of a field element rather than hex.
    let bytes: Vec<u8> = if s.chars().all(|c| c.is_ascii_digit()) {
        use num_bigint::BigUint;
        let n =
            BigUint::parse_bytes(s.as_bytes(), 10).ok_or_else(|| "invalid decimal".to_string())?;
        let mut b = n.to_bytes_be();
        if b.len() > 32 {
            return Err("decimal too large for 256-bit".to_string());
        }
        // left pad
        if b.len() < 32 {
            let mut padded = vec![0u8; 32 - b.len()];
            padded.extend_from_slice(&b);
            b = padded;
        }
        b
    } else {
        // Hex path
        let mut clean = s.trim_start_matches("0x").to_string();
        if clean.len() % 2 == 1 {
            clean = format!("0{}", clean);
        }
        hex::decode(clean).map_err(|e| format!("invalid hex: {e}"))?
    };
    if bytes.len() > 32 {
        return Err(format!("hex string too long ({} bytes > 32)", bytes.len()));
    }
    // Left-pad with zeros to 32 bytes
    let mut buf = [0u8; 32];
    buf[32 - bytes.len()..].copy_from_slice(&bytes);
    let arr: [u8; 32] = buf;
    Ok(arr.into())
}

/// Poseidon hasher implementing `sparse_merkle_tree::Hasher` over BN254.
#[derive(Default)]
pub struct PoseidonHasher(Vec<u8>);

impl sparse_merkle_tree::traits::Hasher for PoseidonHasher {
    fn write_h256(&mut self, h: &H256) {
        self.0.extend_from_slice(h.as_slice());
    }

    fn write_byte(&mut self, b: u8) {
        self.0.push(b);
    }

    fn finish(self) -> H256 {
        match self.0.len() {
            0 => H256::zero(),
            32 => {
                // Identity for single input (leaf): return the value unchanged
                let arr: [u8; 32] = self.0[..32].try_into().expect("slice len 32");
                arr.into()
            }
            64 => {
                // Two concatenated child hashes -> Poseidon hash_2(left,right)
                let left_bytes: [u8; 32] = self.0[..32].try_into().expect("left 32");
                let right_bytes: [u8; 32] = self.0[32..64].try_into().expect("right 32");

                let left_fe = Bn128FieldElement::from_biguint(&BigUint::from_bytes_be(&left_bytes));
                let right_fe =
                    Bn128FieldElement::from_biguint(&BigUint::from_bytes_be(&right_bytes));

                let out_fe = poseidon(2, &[left_fe, right_fe]).expect("poseidon hash");
                let mut bytes = out_fe.to_biguint().to_bytes_be();
                if bytes.len() < 32 {
                    let mut pad = vec![0u8; 32 - bytes.len()];
                    pad.append(&mut bytes);
                    bytes = pad;
                } else if bytes.len() > 32 {
                    bytes = bytes[bytes.len() - 32..].to_vec();
                }
                let arr: [u8; 32] = bytes.try_into().expect("length 32");
                arr.into()
            }
            _ => {
                // Unexpected length – fall back to hashing entire buffer to 1 element to maintain consistency
                let n = BigUint::from_bytes_be(&self.0);
                let fe = Bn128FieldElement::from_biguint(&n);
                let out_fe = poseidon(1, &[fe]).expect("poseidon hash");
                let mut bytes = out_fe.to_biguint().to_bytes_be();
                if bytes.len() < 32 {
                    let mut pad = vec![0u8; 32 - bytes.len()];
                    pad.append(&mut bytes);
                    bytes = pad;
                } else if bytes.len() > 32 {
                    bytes = bytes[bytes.len() - 32..].to_vec();
                }
                let arr: [u8; 32] = bytes.try_into().expect("length 32");
                arr.into()
            }
        }
    }
}

/// A sparse Merkle tree using Poseidon hash function.
#[derive(Default)]
pub struct CommitmentSet {
    tree: SparseMerkleTree<PoseidonHasher, One, DefaultStore<One>>,
}

impl CommitmentSet {
    /// Obtain a clone of the underlying DefaultStore (useful for snapshotting).
    #[allow(dead_code)]
    pub fn store_clone(&self) -> DefaultStore<One> {
        self.tree.store().clone()
    }

    /// Rebuild a commitment set from a root hash and an already-filled store.
    #[allow(dead_code)]
    pub fn from_parts(root: H256, store: DefaultStore<One>) -> Self {
        let tree = SparseMerkleTree::<PoseidonHasher, One, _>::new(root, store);
        Self { tree }
    }
}

impl CommitmentSet {
    /// Derive the first 16 Merkle siblings (bottom-up) plus direction bits for `key`.
    /// Returned tuple: (siblings_hex, index_bits)
    pub fn merkle_path_16(&self, key: &H256) -> (Vec<String>, Vec<bool>) {
        // Generate full proof from library (covers all 256 levels)
        let proof = match self.tree.merkle_proof(vec![*key]) {
            Ok(p) => p,
            Err(_) => return (vec!["0".to_string(); 16], vec![false; 16]),
        };

        let (bitmaps, siblings) = proof.take();
        let bitmap = bitmaps.get(0).cloned().unwrap_or_else(H256::zero);

        let mut sib_iter = siblings.into_iter();
        let mut out_sibs = Vec::with_capacity(16);
        let mut out_bits = Vec::with_capacity(16);

        for height in 0u8..16u8 {
            let is_right = key.get_bit(height);
            out_bits.push(is_right);

            let sibling_hash = if bitmap.get_bit(height) {
                if let Some(mv) = sib_iter.next() {
                    mv.hash::<PoseidonHasher>()
                } else {
                    H256::zero()
                }
            } else {
                H256::zero()
            };

            let bytes: [u8; 32] = sibling_hash.into();
            out_sibs.push(hex::encode(bytes));
        }

        (out_sibs, out_bits)
    }
}

/// Convenience helper to convert an `H256` back into a lowercase hex string.
#[allow(dead_code)]
pub fn h256_to_hex(h: &H256) -> String {
    let bytes: [u8; 32] = (*h).into();
    hex::encode(bytes)
}

impl CommitmentSet {
    /// Create an empty tree (all leaves initialised to zero).
    pub fn new() -> Self {
        Self {
            tree: SparseMerkleTree::<PoseidonHasher, One, DefaultStore<One>>::default(),
        }
    }

    /// Insert a commitment `C` as **key** with constant leaf value `1`.
    pub fn insert(&mut self, key: H256) {
        let _ = self.tree.update(key, One);
    }

    /// Check whether a commitment key exists in the tree.
    pub fn contains(&self, key: &H256) -> bool {
        self.tree.store().leaves_map().contains_key(key)
    }

    /// Generate a Merkle proof for one leaf under the current root.
    #[allow(dead_code)]
    pub fn merkle_proof(
        &self,
        key: &H256,
    ) -> Result<sparse_merkle_tree::MerkleProof, sparse_merkle_tree::error::Error> {
        self.tree.merkle_proof(vec![*key])
    }

    /// Verify a compiled Merkle proof of (`key`, `1`) against the current root.
    #[allow(dead_code)]
    pub fn verify_proof(&self, key: &H256, proof: CompiledMerkleProof) -> bool {
        let mut one_bytes = [0u8; 32];
        one_bytes[31] = 1;
        let one_hash: H256 = one_bytes.into();
        match proof.compute_root::<PoseidonHasher>(vec![(*key, one_hash)]) {
            Ok(root) => root == *self.tree.root(),
            Err(_) => false,
        }
    }

    /// Return the current root hash of the tree.
    pub fn root(&self) -> H256 {
        *self.tree.root()
    }

    /// Borrow the underlying DefaultStore (read-only).
    #[allow(dead_code)]
    pub fn store(&self) -> &DefaultStore<One> {
        self.tree.store()
    }
}