# PyR0 - Python Interface for RISC Zero zkVM

Python bindings for [RISC Zero](https://www.risczero.com/) zkVM, enabling zero-knowledge proof generation and verification from Python.

## Overview

PyR0 provides a Python interface to RISC Zero's zero-knowledge virtual machine, allowing you to:
- Execute RISC Zero guest programs from Python
- Generate and verify zero-knowledge proofs
- Build Merkle trees with Poseidon hash for ZK circuits
- Serialize data for guest program inputs

## Installation

### Prerequisites

- Python 3.8+
- Rust toolchain
- [uv](https://docs.astral.sh/uv/) package manager
- **Currently requires Apple Silicon Mac (M1/M2/M3)** - Intel Mac and Linux support coming soon

### Building from Source (Apple Silicon)

```bash
# Clone the repository
git clone https://github.com/garyrob/PyR0.git
cd PyR0

# Build and install with uv
uv tool run maturin build --release
uv pip install --force-reinstall target/wheels/PyR0-*-macosx_11_0_arm64.whl
```

### Building from Source (Other Platforms)

For Intel Macs, Linux, or Windows, you'll need to build from source:

```bash
# Clone the repository
git clone https://github.com/garyrob/PyR0.git
cd PyR0

# Build for your platform
uv tool run maturin build --release

# Install the wheel (filename will vary by platform)
uv pip install --force-reinstall target/wheels/PyR0-*.whl
```

Note: The RISC Zero library itself has platform-specific requirements and may require additional setup on non-Mac platforms.

For development with editable installs, see [CLAUDE.md](CLAUDE.md) for important notes about uv's behavior.

## Features

### Core RISC Zero Operations

Execute guest programs and generate proofs:

```python
import pyr0

# Load a RISC Zero guest program
with open("guest_program.elf", "rb") as f:
    elf_data = f.read()
image = pyr0.load_image_from_elf(elf_data)

# Execute with input
input_data = pyr0.prepare_input(b"your input data")
segments, info = pyr0.execute_with_input(image, input_data)

# Generate a proof
receipt = pyr0.prove_segment(segments[0])

# Verify the proof
pyr0.verify_receipt(receipt)
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

# Serialize various data types for guest programs
data = serialization.vec_u8(bytes_data)  # Vec<u8> with length prefix
data = serialization.u32(value)          # 32-bit unsigned integer
data = serialization.u64(value)          # 64-bit unsigned integer
data = serialization.string(text)        # String with length prefix

# Prepare Ed25519 signature verification input
input_data = serialization.ed25519_input_vecs(public_key, signature, message)
```

## Examples

### Ed25519 Signature Verification

See [demo/real_ed25519_test.py](demo/real_ed25519_test.py) for a complete example of:
- Building a RISC Zero guest program that verifies Ed25519 signatures
- Generating zero-knowledge proofs of signature validity
- Verifying program identity via ImageID

### Merkle Tree Operations

See [demo/merkle_demo.py](demo/merkle_demo.py) for examples of:
- Building sparse Merkle trees
- Generating Merkle proofs for zero-knowledge circuits
- Using Poseidon hash over BN254 field

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
└── CLAUDE.md         # Development notes
```

## Development

This project uses [maturin](https://www.maturin.rs/) for building Python extensions from Rust. Key commands:

```bash
# Build for development
uv tool run maturin develop

# Build release wheel
uv tool run maturin build --release

# Run tests/demos
uv run demo/real_ed25519_test.py
uv run demo/merkle_demo.py
```

## Acknowledgments

This project is based on the original [PyR0](https://github.com/l2iterative/pyr0prover-python) by L2 Iterative, which focused on distributed proof generation using Dask/Ray. The current fork extends PyR0 with additional features for zero-knowledge proof development, including Merkle tree support and improved guest program interfaces.

## License

This project is dual-licensed under either:

- MIT license ([LICENSE](LICENSE))
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))

You may choose either license for your use case.

See [NOTICE](NOTICE) for attribution and details about the original project.