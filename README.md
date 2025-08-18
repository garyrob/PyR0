# PyR0 - Python Interface for RISC Zero zkVM

[![Version](https://img.shields.io/badge/version-0.5.1-orange)](https://github.com/garyrob/PyR0/releases)
**⚠️ Experimental Alpha - Apple Silicon Only**

Python bindings for [RISC Zero](https://www.risczero.com/) zkVM, enabling zero-knowledge proof generation and verification from Python.

> **Note**: This is an experimental alpha release (v0.5.1) currently targeting Apple Silicon (M1/M2/M3) Macs only.

## Overview

PyR0 provides a Python interface to RISC Zero's zero-knowledge virtual machine, allowing you to:
- Execute RISC Zero guest programs from Python
- Generate and verify zero-knowledge proofs
- Build Merkle trees with Poseidon hash for ZK circuits
- Serialize data for guest program inputs

### Architecture

PyR0 bridges Python and RISC Zero zkVM:

1. **Host (Python)**: Prepares input data, loads guest programs, generates proofs
2. **Guest (Rust)**: Executes in zkVM, reads input, writes output to journal
3. **Proof**: Cryptographic evidence that the guest executed correctly

The typical workflow:
1. Write a Rust guest program that performs your computation
2. Compile it to RISC-V ELF binary
3. Use PyR0 to load the ELF, provide input, and generate a proof
4. Share the proof and journal (public outputs) for verification

## Guest Program Development

### Basic Guest Setup

A minimal RISC Zero guest program requires proper configuration:

**Cargo.toml:**
```toml
[package]
name = "my-guest"
version = "0.1.0"
edition = "2021"

[dependencies]
# Basic setup - works for simple guests
risc0-zkvm = { version = "1.2", default-features = false, features = ["std"] }
```

### Memory Management

⚠️ **Critical for complex guests**: The default bump allocator never frees memory, causing "Out of memory!" errors even with moderate data.

Enable the heap allocator for guests that:
- Process variable-length data
- Use collections (Vec, HashMap, etc.)
- Perform string operations
- Run iterative algorithms

```toml
[dependencies]
risc0-zkvm = { version = "1.2", default-features = false, features = ["std", "heap-embedded-alloc"] }
```

*Note: The heap allocator adds ~5% cycle overhead but prevents memory exhaustion.*

### Common Guest Patterns

**Reading Input:**
```rust
// For raw bytes (most efficient, works with pyr0.prove(image, raw_bytes))
use std::io::Read;
let mut buffer = Vec::new();
env::stdin().read_to_end(&mut buffer).unwrap();

// For serialized data (when using PyR0 serialization helpers)
let data: MyStruct = env::read();
```

**Writing to Journal:**
```rust
// Simple values
env::commit(&my_u32);

// Complex structures (using Borsh)
use borsh::BorshSerialize;
let output = MyOutput { /* ... */ };
env::commit_slice(&borsh::to_vec(&output).unwrap());
```

## Installation

### System Requirements

**This alpha release requires:**
- Apple Silicon Mac (M1, M2, or M3)
- macOS 11.0 or later
- Python 3.8.3+
- Rust toolchain with cargo
- RISC Zero toolchain (`cargo risczero` installed via `cargo install cargo-risczero`)
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

### Building Guest Programs

PyR0 can build RISC Zero guest programs directly:

```python
import pyr0

# Build a guest program (always rebuilds to ensure up-to-date)
elf_path = pyr0.build_guest("path/to/guest", "binary-name")

# Auto-detect binary name from Cargo.toml
elf_path = pyr0.build_guest("path/to/guest")

# Build in debug mode (faster compile, slower execution)
elf_path = pyr0.build_guest("path/to/guest", release=False)
```

The `build_guest` function:
- Always rebuilds to ensure the ELF is up-to-date
- Handles both standard (embed_methods) and direct build structures
- Automatically detects the correct build method
- Returns the path to the built ELF file
- Raises `GuestBuildFailedError` if compilation fails
- Raises `InvalidGuestDirectoryError` if the directory is invalid
- Raises `ElfNotFoundError` if the ELF isn't found after building

### Core RISC Zero Operations

Execute guest programs and generate proofs:

```python
import pyr0

# Option 1: Build and load a guest program
elf_path = pyr0.build_guest("path/to/guest", "binary-name")
with open(elf_path, "rb") as f:
    elf_data = f.read()
image = pyr0.load_image(elf_data)

# Option 2: Load a pre-built ELF
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

PyR0 provides serialization helpers for sending data to RISC Zero guest programs. The choice of serialization method depends on how your guest reads the data:

#### For Guests Using `env::read()`

These helpers add length prefixes and are designed for serde deserialization:

```python
from pyr0 import serialization

# These work with env::read() in the guest
data = serialization.to_vec_u8(bytes_data)  # Vec<u8> with length prefix
data = serialization.to_u32(value)          # u32 (4 bytes, little-endian)
data = serialization.to_u64(value)          # u64 (8 bytes, little-endian)
data = serialization.to_string(text)        # String with 8-byte length prefix
data = serialization.to_bool(value)         # bool (single byte: 0 or 1)

# Guest code would use:
# let data: Vec<u8> = env::read();
# let value: u32 = env::read();
# let text: String = env::read();
```

#### For Guests Using `env::read_slice()`

These helpers provide raw bytes without length prefixes:

```python
# Fixed-size arrays (no length prefix)
data = serialization.to_bytes32(data)       # [u8; 32] - exactly 32 bytes
data = serialization.to_bytes64(data)       # [u8; 64] - exactly 64 bytes
data = serialization.raw_bytes(data)        # Raw bytes, no transformation

# Guest code would use:
# let mut buffer = [0u8; 32];
# env::read_slice(&mut buffer);
```

#### Convenience Functions

Pre-built serializers for common cryptographic operations:

```python
# For Ed25519 signature verification (uses env::read() format)
input_data = serialization.ed25519_input(public_key, signature, message)

# For Merkle proofs with 2LA-style commitments (uses env::read_slice() format)
# Note: Expects exactly 16 siblings for a 16-level tree
input_data = serialization.merkle_commitment_input(k_pub, r, e, siblings, indices)
```

#### Choosing Between `env::read()` and `env::read_slice()`

**Use `env::read()` when:**
- Data sizes are variable
- You want automatic deserialization
- You're using standard Rust types (Vec, String, etc.)
- You don't know the exact size in advance

**Use `env::read_slice()` when:**
- Data size is fixed and known
- You want maximum efficiency (no overhead)
- You're working with raw bytes
- You want to avoid serde overhead

**Example: Sending mixed data types**

```python
# Python host code
from pyr0 import serialization

# Combine different serialization methods
input_data = b""
input_data += serialization.to_u32(42)           # 4 bytes (for env::read)
input_data += serialization.to_bytes32(key)      # 32 bytes (for env::read_slice)
input_data += serialization.to_string("hello")   # Variable (for env::read)

receipt = pyr0.prove(image, input_data)
```

```rust
// Rust guest code
use risc0_zkvm::guest::env;

fn main() {
    // Read the u32 with serde
    let number: u32 = env::read();
    
    // Read the fixed array with read_slice
    let mut key = [0u8; 32];
    env::read_slice(&mut key);
    
    // Read the string with serde
    let text: String = env::read();
}
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

## Common Pitfalls

### Serialization Mismatches

The most common error is mismatched serialization between host and guest:

```python
# WRONG: Host uses to_vec_u8 (adds length prefix)
input_data = serialization.to_vec_u8(my_bytes)
```

```rust
// WRONG: Guest uses read_slice (expects raw bytes)
let mut buffer = [0u8; 32];
env::read_slice(&mut buffer);  // Will read length prefix as data!
```

**Solution**: Match serialization methods:
- `to_vec_u8()` ↔ `env::read::<Vec<u8>>()`
- `to_bytes32()` or `raw_bytes()` ↔ `env::read_slice()`

### Size Mismatches

When using `env::read_slice()`, the buffer size must match exactly:

```rust
// Guest expects exactly 100 bytes
let mut buffer = [0u8; 100];
env::read_slice(&mut buffer);
```

```python
# Host must send exactly 100 bytes
input_data = serialization.raw_bytes(b"x" * 100)  # Correct
input_data = serialization.raw_bytes(b"x" * 99)   # Wrong - too short!
```

### Journal Format

The journal (public output) should use a consistent serialization format. We recommend Borsh for cross-language compatibility:

```rust
// Guest: Write with Borsh
use borsh::BorshSerialize;
let output = MyOutput { ... };
env::commit_slice(&borsh::to_vec(&output)?);
```

```python
# Host: Read with Borsh
from borsh_construct import CStruct
output = OutputSchema.parse(receipt.journal)
```

## Development

This project uses [maturin](https://www.maturin.rs/) for building Python extensions from Rust. Key commands:

```bash
# Build release wheel
uv tool run maturin build --release

# Install the built wheel (force reinstall to avoid cache issues)
uv pip install --force-reinstall target/wheels/PyR0-0.2.0-*.whl

# Run tests/demos
uv run demo/ed25519_demo.py
uv run demo/merkle_zkp_demo.py
uv run test/test_merkle_zkp.py
```

### Important Build Notes

After making changes to ANY file (Rust or Python), you must rebuild and reinstall:
1. Build: `uv tool run maturin build --release`
2. Install: `uv pip install --force-reinstall target/wheels/PyR0-*.whl`

The `--force-reinstall` flag is crucial to ensure you're using the latest version.

## Acknowledgments

This project is based on the original [PyR0](https://github.com/l2iterative/pyr0prover-python) by L2 Iterative, which focused on distributed proof generation using Dask/Ray. The current fork extends PyR0 with additional features for zero-knowledge proof development, including Merkle tree support and improved guest program interfaces.

## License

This project is dual-licensed under either:

- MIT license ([LICENSE](LICENSE))
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))

You may choose either license for your use case.

See [NOTICE](NOTICE) for attribution and details about the original project.