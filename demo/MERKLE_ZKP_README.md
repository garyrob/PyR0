# Merkle Zero-Knowledge Proof Demo

This demonstrates how to create privacy-preserving membership proofs using RISC Zero, equivalent to the Noir 2LA circuits.

## What This Does

The demo implements a zero-knowledge proof system that allows a user to prove they are in a Merkle tree WITHOUT revealing:
- Which leaf they are
- Their private data (randomness, nullifier)
- The Merkle path they used

This is the core functionality of the 2LA (Two-Layer Authentication) protocol.

## Files

- `merkle_zkp_demo.py` - Complete demo showing the full workflow
- `merkle_proof_guest/` - RISC Zero guest program (Rust) that verifies Merkle proofs
- `test_merkle_zkp.py` - Simple test script to verify everything works
- `merkle_demo.py` - Basic Merkle tree operations (no ZKP)

## How It Works

### 1. Setup Phase
- Multiple users register with commitments: `C = Hash(k_pub || r || e)`
- All commitments are inserted into a Merkle tree
- The Merkle root is made public

### 2. Proving Phase (Private)
The prover:
- Selects their identity (which user they are)
- Generates a Merkle proof path from their leaf to the root
- Runs the RISC Zero guest program with their private inputs
- Generates a zero-knowledge proof

### 3. Verification Phase (Public)
The verifier:
- Receives only the proof and the expected Merkle root
- Verifies the proof is valid
- Learns that SOMEONE is in the tree, but not WHO

## Running the Demo

```bash
# From the PyR0 repository root (/Users/garyrob/Source/pyr0)

# Run the full demonstration
uv run python demo/merkle_zkp_demo.py

# Or run the test script (checks components first)
uv run python test/test_merkle_zkp.py
```

### Script Differences

- **`merkle_zkp_demo.py`**: The complete demonstration with educational output showing the privacy-preserving proof workflow
- **`test_merkle_zkp.py`**: Diagnostic tool that tests each component individually before running the demo

## Requirements

- PyR0 installed (for RISC Zero proof generation)
- merkle_py installed (for Merkle tree operations)
- (Optional) RISC Zero toolchain for rebuilding the guest program

## Comparison to Noir 2LA

This RISC Zero implementation is functionally equivalent to the Noir 2LA circuit:

| Noir 2LA | RISC Zero (This Demo) |
|----------|----------------------|
| `pedersen_hash` for commitments | SHA256 for commitments |
| `MerkleTree::calculate_root` | Manual path traversal |
| Noir circuit constraints | RISC Zero zkVM execution |
| Returns `(root, e_computed)` | Returns `(root, k_pub)` |

Both prove the same thing: knowledge of a valid Merkle path without revealing which one.

## Expert Question for Optimization

The current implementation uses SHA256 for hashing. For better efficiency in ZK circuits, we should ask:

**"Are there RISC Zero-optimized implementations of Poseidon hash or other ZK-friendly hash functions that work well in the zkVM? The Python side already uses Poseidon via merkle_py, but the guest program uses SHA256."**

## Privacy Guarantees

The zero-knowledge proof ensures:
- ✅ Prover demonstrates valid membership
- ✅ Verifier cannot determine which member
- ✅ No private data is revealed
- ✅ Proof cannot be replayed (each proof is unique)

This enables anonymous authentication use cases like:
- Anonymous voting
- Privacy-preserving identity verification
- Confidential access control

## Example Output

When you run the demo, you'll see:

```
STEP 1: Creating 8 users with commitments
STEP 2: Building Merkle tree (root is PUBLIC)
STEP 3: Prover selects User 3 (PRIVATE)
STEP 4: Generating Merkle proof (PRIVATE)
STEP 5: Creating zero-knowledge proof...
STEP 6: Verifier checks proof (knows NOTHING about which user)
✓ Proof is VALID!
```

The key insight: The verifier confirms someone is in the tree without learning who.