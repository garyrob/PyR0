"""
Sparse Merkle tree implementation with Poseidon hash for zero-knowledge proofs.

This module provides a Python interface to a sparse Merkle tree implementation
that uses Poseidon hash over BN254, compatible with zero-knowledge circuits.
"""

from merkle_py._rust import (
    MerkleTree,
    poseidon_hash,
    hex_to_bytes,
    bytes_to_hex,
)

__all__ = [
    "MerkleTree",
    "poseidon_hash", 
    "hex_to_bytes",
    "bytes_to_hex",
]

__version__ = "0.1.0"