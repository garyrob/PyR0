"""
Serialization helpers for preparing data to send to RISC Zero guest programs.

This module provides:
1. Basic primitives for serializing Python data to Rust types
2. Convenience functions for common cryptographic operations (Ed25519, Merkle proofs)
3. Helper patterns for standard RISC Zero use cases

These are optional convenience functions - you can use them directly or as 
examples for building your own serialization logic.
"""

import struct
from typing import Union, List


def to_vec_u8(data: Union[bytes, bytearray, List[int]]) -> bytes:
    """
    Serialize data as Rust Vec<u8> for RISC Zero's serde format.
    
    IMPORTANT: RISC Zero's serde::to_vec returns Vec<u32>, where each u8 
    is stored as a u32 word. So we need to match that format.
    
    Format: 
    - First word (4 bytes): length as u32
    - Following words: each byte as a u32 (4 bytes per original byte)
    
    Args:
        data: Bytes-like data or list of integers (0-255)
    
    Returns:
        Serialized bytes in RISC Zero format
    
    Example:
        >>> to_vec_u8(b"AB")  # 2 bytes
        # Results in: length(2) + A as u32 + B as u32 = 12 bytes total
    """
    if isinstance(data, (list, tuple)):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, bytes):
        # Try to convert other types
        if hasattr(data, 'tobytes'):  # numpy arrays, array.array
            data = data.tobytes()
        else:
            data = bytes(data)
    
    # Pack length as u32
    result = struct.pack('<I', len(data))
    
    # Pack each byte as a u32 word (little-endian)
    for byte in data:
        result += struct.pack('<I', byte)
    
    return result


def to_bytes32(data: Union[bytes, bytearray, List[int]]) -> bytes:
    """
    Serialize data as Rust [u8; 32] (fixed-size array).
    
    Format: Exactly 32 bytes, no length prefix
    
    Args:
        data: Exactly 32 bytes of data
    
    Returns:
        Raw 32 bytes
    
    Raises:
        ValueError: If data is not exactly 32 bytes
    """
    if isinstance(data, (list, tuple)):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, bytes):
        if hasattr(data, 'tobytes'):
            data = data.tobytes()
        else:
            data = bytes(data)
    
    if len(data) != 32:
        raise ValueError(f"Expected exactly 32 bytes, got {len(data)}")
    
    return data


def to_bytes64(data: Union[bytes, bytearray, List[int]]) -> bytes:
    """
    Serialize data as Rust [u8; 64] (fixed-size array).
    
    Format: Exactly 64 bytes, no length prefix
    
    Args:
        data: Exactly 64 bytes of data
    
    Returns:
        Raw 64 bytes
    
    Raises:
        ValueError: If data is not exactly 64 bytes
    """
    if isinstance(data, (list, tuple)):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, bytes):
        if hasattr(data, 'tobytes'):
            data = data.tobytes()
        else:
            data = bytes(data)
    
    if len(data) != 64:
        raise ValueError(f"Expected exactly 64 bytes, got {len(data)}")
    
    return data


def to_u32(value: int) -> bytes:
    """
    Serialize an integer as Rust u32.
    
    Format: 4 bytes, little-endian
    
    Args:
        value: Integer value (0 to 2^32-1)
    
    Returns:
        4 bytes in little-endian format
    
    Raises:
        struct.error: If value is out of range for u32
    """
    return struct.pack('<I', value)


def to_u64(value: int) -> bytes:
    """
    Serialize an integer as Rust u64.
    
    Format: 8 bytes, little-endian
    
    Args:
        value: Integer value (0 to 2^64-1)
    
    Returns:
        8 bytes in little-endian format
    
    Raises:
        struct.error: If value is out of range for u64
    """
    return struct.pack('<Q', value)


def to_string(text: str) -> bytes:
    """
    Serialize a string as Rust String.
    
    Format: 8-byte length (u64) + UTF-8 encoded bytes
    
    Args:
        text: String to serialize
    
    Returns:
        Serialized string with length prefix
    """
    encoded = text.encode('utf-8')
    return struct.pack('<Q', len(encoded)) + encoded


def to_bool(value: bool) -> bytes:
    """
    Serialize a boolean as Rust bool.
    
    Format: Single byte (0 or 1)
    
    Args:
        value: Boolean value
    
    Returns:
        Single byte: b'\\x00' for False, b'\\x01' for True
    """
    return b'\x01' if value else b'\x00'


def raw_bytes(data: Union[bytes, bytearray, List[int]]) -> bytes:
    """
    Pass through raw bytes without any transformation or length prefix.
    
    This is useful when the guest code uses env::read_slice() with a 
    buffer of known size, avoiding the overhead of serde serialization.
    
    Format: Raw bytes, no prefix or transformation
    
    Args:
        data: Bytes to pass through
    
    Returns:
        The exact bytes provided
    
    Example:
        >>> raw_bytes(b"hello")
        b'hello'  # Just 5 bytes, no length prefix
    """
    if isinstance(data, (list, tuple)):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, bytes):
        if hasattr(data, 'tobytes'):
            data = data.tobytes()
        else:
            data = bytes(data)
    
    return data


# ============================================================================
# Convenience functions for common cryptographic patterns
# ============================================================================

def ed25519_input(public_key: bytes, signature: bytes, message: bytes) -> bytes:
    """
    Serialize Ed25519 verification input as three Vec<u8> values.
    Alias for ed25519_input_vecs for cleaner API.
    
    Guest code would read this as:
        let public_key: Vec<u8> = env::read();
        let signature: Vec<u8> = env::read();
        let message: Vec<u8> = env::read();
    
    Args:
        public_key: 32-byte public key
        signature: 64-byte signature
        message: Variable-length message
    
    Returns:
        Serialized bytes ready for pyr0.prove() or execute_with_input()
    
    Example:
        input_data = ed25519_input(pk_bytes, sig_bytes, msg_bytes)
        receipt = pyr0.prove(image, input_data)
    """
    return to_vec_u8(public_key) + to_vec_u8(signature) + to_vec_u8(message)


def ed25519_input_vecs(public_key: bytes, signature: bytes, message: bytes) -> bytes:
    """
    Serialize Ed25519 verification input as three Vec<u8> values.
    
    Guest code would read this as:
        let public_key: Vec<u8> = env::read();
        let signature: Vec<u8> = env::read();
        let message: Vec<u8> = env::read();
    
    Args:
        public_key: 32-byte public key
        signature: 64-byte signature
        message: Variable-length message
    
    Returns:
        Serialized bytes ready for pyr0.prove() or execute_with_input()
    
    Example:
        input_data = ed25519_input_vecs(pk_bytes, sig_bytes, msg_bytes)
        receipt = pyr0.prove(image, input_data)
    """
    return to_vec_u8(public_key) + to_vec_u8(signature) + to_vec_u8(message)


def ed25519_input_arrays(public_key: bytes, signature: bytes, message: bytes) -> bytes:
    """
    Serialize Ed25519 verification input with fixed arrays for key and signature.
    More efficient than Vec<u8> for fixed-size data.
    
    Guest code would read this as:
        let public_key: [u8; 32] = env::read();
        let signature: [u8; 64] = env::read();
        let message: Vec<u8> = env::read();
    
    Args:
        public_key: 32-byte public key
        signature: 64-byte signature
        message: Variable-length message
    
    Returns:
        Serialized bytes ready for pyr0.prove() or execute_with_input()
    
    Example:
        input_data = ed25519_input_arrays(pk_bytes, sig_bytes, msg_bytes)
        receipt = pyr0.prove(image, input_data)
    """
    return to_bytes32(public_key) + to_bytes64(signature) + to_vec_u8(message)


def merkle_proof_input(leaf_data: bytes, siblings: List[bytes], indices: List[bool]) -> bytes:
    """
    Serialize input for a Merkle proof verification.
    
    Guest code would read this as:
        let leaf: [u8; 32] = env::read();
        let siblings: Vec<[u8; 32]> = env::read();
        let indices: Vec<bool> = env::read();
    
    Args:
        leaf_data: 32-byte leaf hash
        siblings: List of 32-byte sibling hashes
        indices: List of boolean path bits (left=False, right=True)
    
    Returns:
        Serialized bytes ready for pyr0.prove() or execute_with_input()
    
    Example:
        input_data = merkle_proof_input(leaf_hash, path_siblings, path_bits)
        receipt = pyr0.prove(image, input_data)
    """
    # Serialize leaf as fixed array
    result = to_bytes32(leaf_data)
    
    # Serialize siblings as Vec<[u8; 32]>
    result += to_u64(len(siblings))  # Vec length
    for sibling in siblings:
        result += to_bytes32(sibling)
    
    # Serialize indices as Vec<bool>
    result += to_u64(len(indices))  # Vec length
    for bit in indices:
        result += to_bool(bit)
    
    return result


def merkle_commitment_input(k_pub: bytes, r: bytes, e: bytes, 
                           siblings: List[bytes], indices: List[bool]) -> bytes:
    """
    Serialize input for a Merkle commitment proof (2LA-style).
    
    This is for proving knowledge of a commitment C = Hash(k_pub || r || e)
    that exists in a Merkle tree, without revealing r, e, or the path.
    
    Guest code would read this as:
        let k_pub: [u8; 32] = env::read();
        let r: [u8; 32] = env::read();
        let e: [u8; 32] = env::read();
        let siblings: Vec<[u8; 32]> = env::read();
        let indices: Vec<bool> = env::read();
    
    Args:
        k_pub: 32-byte public key
        r: 32-byte randomness (secret)
        e: 32-byte external identity nullifier (secret)
        siblings: List of 32-byte sibling hashes in Merkle path
        indices: List of boolean path bits
    
    Returns:
        Serialized bytes ready for pyr0.prove() or execute_with_input()
    """
    result = to_bytes32(k_pub)
    result += to_bytes32(r)
    result += to_bytes32(e)
    
    # Serialize Merkle path
    result += to_u64(len(siblings))
    for sibling in siblings:
        result += to_bytes32(sibling)
    
    result += to_u64(len(indices))
    for bit in indices:
        result += to_bool(bit)
    
    return result