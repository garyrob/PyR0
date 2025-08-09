"""
Serialization helpers for preparing data to send to RISC Zero guest programs.

These functions serialize Python data into the binary format expected by 
Rust's bincode deserializer used in env::read().
"""

import struct
from typing import Union, List


def vec_u8(data: Union[bytes, bytearray, List[int]]) -> bytes:
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
        >>> vec_u8(b"AB")  # 2 bytes
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


def array_u8_32(data: Union[bytes, bytearray, List[int]]) -> bytes:
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


def array_u8_64(data: Union[bytes, bytearray, List[int]]) -> bytes:
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


def u32(value: int) -> bytes:
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


def u64(value: int) -> bytes:
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


def string(text: str) -> bytes:
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


def bool_value(value: bool) -> bytes:
    """
    Serialize a boolean as Rust bool.
    
    Format: Single byte (0 or 1)
    
    Args:
        value: Boolean value
    
    Returns:
        Single byte: b'\\x00' for False, b'\\x01' for True
    """
    return b'\x01' if value else b'\x00'


# Convenience functions for common patterns

def ed25519_input_vecs(public_key: bytes, signature: bytes, message: bytes) -> bytes:
    """
    Serialize Ed25519 verification input as three Vec<u8> values.
    This matches the current guest implementation.
    
    Args:
        public_key: 32-byte public key
        signature: 64-byte signature
        message: Variable-length message
    
    Returns:
        Serialized data ready for prepare_input()
    """
    return vec_u8(public_key) + vec_u8(signature) + vec_u8(message)


def ed25519_input_arrays(public_key: bytes, signature: bytes, message: bytes) -> bytes:
    """
    Serialize Ed25519 verification input with fixed arrays for key and signature.
    More efficient than Vec<u8> for fixed-size data.
    
    Guest would read as:
        let public_key: [u8; 32] = env::read();
        let signature: [u8; 64] = env::read();
        let message: Vec<u8> = env::read();
    
    Args:
        public_key: 32-byte public key
        signature: 64-byte signature
        message: Variable-length message
    
    Returns:
        Serialized data ready for prepare_input()
    """
    return array_u8_32(public_key) + array_u8_64(signature) + vec_u8(message)