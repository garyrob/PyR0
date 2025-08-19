"""Type stubs for PyR0 serialization module."""

from typing import Union, List

# For env::read() - with length prefixes
def to_u32(value: int) -> bytes:
    """Serialize u32 for env::read() (4 bytes, little-endian)."""
    ...

def to_u64(value: int) -> bytes:
    """Serialize u64 for env::read() (8 bytes, little-endian)."""
    ...

def to_vec_u8(data: Union[bytes, bytearray]) -> bytes:
    """Serialize Vec<u8> with u64 length prefix for env::read()."""
    ...

def to_string(text: str) -> bytes:
    """Serialize String with u64 length prefix for env::read()."""
    ...

def to_bool(value: bool) -> bytes:
    """Serialize bool for env::read() (single byte: 0 or 1)."""
    ...

# For env::read_slice() - raw bytes
def to_bytes32(data: Union[bytes, bytearray]) -> bytes:
    """Ensure exactly 32 bytes for env::read_slice() with [u8; 32]."""
    ...

def to_bytes64(data: Union[bytes, bytearray]) -> bytes:
    """Ensure exactly 64 bytes for env::read_slice() with [u8; 64]."""
    ...

def raw_bytes(data: Union[bytes, bytearray]) -> bytes:
    """Pass through raw bytes for env::read_slice()."""
    ...

# Convenience functions
def ed25519_input(
    public_key: Union[bytes, bytearray],
    signature: Union[bytes, bytearray],
    message: Union[bytes, bytearray]
) -> bytes:
    """
    Create input for Ed25519 signature verification guest.
    
    Args:
        public_key: 32-byte Ed25519 public key
        signature: 64-byte Ed25519 signature
        message: Variable-length message that was signed
    
    Returns:
        Serialized input for the guest program
    """
    ...

def merkle_commitment_input(
    k_pub: Union[bytes, bytearray],
    r: Union[bytes, bytearray],
    e: Union[bytes, bytearray],
    siblings: List[Union[bytes, bytearray]],
    indices: List[int]
) -> bytes:
    """
    Create input for Merkle proof verification with 2LA-style commitments.
    
    Args:
        k_pub: 32-byte public key
        r: 32-byte randomness
        e: 32-byte hash value
        siblings: List of 32-byte sibling hashes (must be exactly 16 for 16-level tree)
        indices: List of path indices (0 or 1) for tree traversal
    
    Returns:
        Serialized input for the guest program
    """
    ...