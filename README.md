# PyR0 - Python Interface for RISC Zero zkVM

[![Version](https://img.shields.io/badge/version-0.1.0-orange)](https://github.com/garyrob/PyR0/releases)
**⚠️ Experimental Alpha - Apple Silicon Only**

Python bindings for [RISC Zero](https://www.risczero.com/) zkVM, enabling zero-knowledge proof generation and verification from Python.

> **Note**: This is an experimental alpha release (v0.1.0) currently targeting Apple Silicon (M1/M2/M3) Macs only.

## Overview

PyR0 provides a Python interface to RISC Zero's zero-knowledge virtual machine, allowing you to:
- Execute RISC Zero guest programs from Python
- Generate and verify zero-knowledge proofs
- Build Merkle trees with Poseidon hash for ZK circuits
- Serialize data for guest program inputs

## Installation

### System Requirements

**This alpha release requires:**
- Apple Silicon Mac (M1, M2, or M3)
- macOS 11.0 or later
- Python 3.8.3+
- Rust toolchain
- [uv](https://docs.astral.sh/uv/) package manager

### Building from Source

```bash
# Clone the repository
git clone https://github.com/garyrob/PyR0.git
cd PyR0

# Build and install with uv
uv tool run maturin build --release
uv pip install --force-reinstall target/wheels/PyR0-*-macosx_11_0_arm64.whl
```

For development with editable installs, see [CLAUDE.md](CLAUDE.md) for important notes about uv's behavior.

## Features

### Core RISC Zero Operations

Execute guest programs and generate proofs:

```python
import pyr0

# Load a RISC Zero guest program
with open("guest_program.elf", "rb") as f:
    elf_data = f.read()
image = pyr0.load_image(elf_data)

# One-step proof generation (execution + proof)
input_data = b"your input data"  # Direct bytes, no wrapper needed
receipt = pyr0.prove(image, input_data)

# Get the journal (public outputs) as a property
journal = receipt.journal

# Verify the proof
receipt.verify()

# Access the image ID
image_id = image.id
```

### Merkle Trees with Poseidon Hash

Build sparse Merkle trees compatible with zero-knowledge circuits:

```python
import merkle_py

# Create a sparse Merkle tree
tree = merkle_py.MerkleTree()

# Insert keys
tree.insert("0x0000000000000000000000000000000000000000000000000000000000000001")
tree.insert("0x0000000000000000000000000000000000000000000000000000000000000002")

# Get the root
root = tree.root()

# Generate a Merkle proof (16 levels for Noir compatibility)
siblings, bits = tree.merkle_path_16(key)

# Use Poseidon hash directly
hash_result = merkle_py.poseidon_hash([input1, input2])
```

### Data Serialization

Prepare data for RISC Zero guest programs:

```python
from pyr0 import serialization

# Optional serialization helpers for guest programs
data = serialization.to_vec_u8(bytes_data)  # Vec<u8> with length prefix
data = serialization.to_u32(value)          # 32-bit unsigned integer
data = serialization.to_u64(value)          # 64-bit unsigned integer
data = serialization.to_string(text)        # String with length prefix
data = serialization.to_bool(value)         # Boolean value
data = serialization.to_bytes32(data)       # Fixed [u8; 32] array
data = serialization.to_bytes64(data)       # Fixed [u8; 64] array

# Convenience functions for common patterns
input_data = serialization.ed25519_input(public_key, signature, message)
input_data = serialization.merkle_proof_input(leaf, siblings, indices)
```

### Journal Deserialization

For cross-language compatibility, guest programs should use Borsh serialization:

```python
from borsh_construct import CStruct, U8, U64

# Define schema matching your Rust struct
OutputSchema = CStruct(
    "field1" / U8[32],   # [u8; 32] in Rust
    "field2" / U64,      # u64 in Rust
)

# Parse journal from receipt
journal = receipt.journal  # Access as property
output = OutputSchema.parse(journal)
```

## Examples

### Ed25519 Signature Verification

See [demo/ed25519_demo.py](demo/ed25519_demo.py) for a complete example of:
- Building a RISC Zero guest program that verifies Ed25519 signatures
- Generating zero-knowledge proofs of signature validity
- Verifying program identity via ImageID

### Merkle Zero-Knowledge Proofs

See [demo/merkle_zkp_demo.py](demo/merkle_zkp_demo.py) for a complete example of:
- Building Merkle trees with user commitments
- Generating zero-knowledge proofs of membership
- Privacy-preserving authentication (proving you're in a set without revealing which member)

## Project Structure

```
PyR0/
├── src/               # Rust source code
│   ├── lib.rs        # Main PyO3 bindings
│   ├── image.rs      # RISC Zero image handling
│   ├── segment.rs    # Proof generation
│   └── receipt.rs    # Proof verification
├── merkle/           # Merkle tree module
│   └── src/          # Merkle tree implementation
├── demo/             # Example scripts
│   ├── merkle_zkp_demo.py     # Merkle ZKP demonstration
│   ├── merkle_proof_guest/    # RISC Zero guest for Merkle proofs
│   └── ed25519_demo.py        # Ed25519 verification demo
├── test/             # Test scripts
└── CLAUDE.md         # Development notes
```

## Development

This project uses [maturin](https://www.maturin.rs/) for building Python extensions from Rust. Key commands:

```bash
# Build release wheel
uv tool run maturin build --release

# Run tests/demos
uv run demo/ed25519_demo.py
uv run demo/merkle_zkp_demo.py
uv run test/test_merkle_zkp.py
```

## Acknowledgments

This project is based on the original [PyR0](https://github.com/l2iterative/pyr0prover-python) by L2 Iterative, which focused on distributed proof generation using Dask/Ray. The current fork extends PyR0 with additional features for zero-knowledge proof development, including Merkle tree support and improved guest program interfaces.

## License

This project is dual-licensed under either:

- MIT license ([LICENSE](LICENSE))
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))

You may choose either license for your use case.

See [NOTICE](NOTICE) for attribution and details about the original project.