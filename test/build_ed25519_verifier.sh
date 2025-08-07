#!/bin/bash
# Script to build the Ed25519 verifier for RISC Zero
# This creates the ELF file needed by ed25519_test.py

set -e

echo "Building Ed25519 Verifier for RISC Zero"
echo "========================================"

# Check if cargo-risczero is installed
if ! command -v cargo-risczero &> /dev/null; then
    echo "Error: cargo-risczero is not installed"
    echo "Install it with: cargo install cargo-risczero"
    exit 1
fi

# Save the original directory (where the script was called from)
ORIGINAL_DIR="$(pwd)"

# Create a temporary directory for the project
TEMP_DIR=$(mktemp -d)
echo "Creating project in: $TEMP_DIR"

cd "$TEMP_DIR"

# Create a new RISC Zero project
echo "Creating RISC Zero project..."
cargo risczero new ed25519-verifier --guest-name method
cd ed25519-verifier

# The cargo risczero new command creates:
# - ed25519-verifier/host/...
# - ed25519-verifier/methods/guest/...
# We need to work in the methods directory and fix the structure

cd methods

# Copy the guest code
echo "Setting up guest code..."
cat > guest/src/main.rs << 'EOF'
#![no_main]
#![no_std]

extern crate alloc;
use alloc::vec;

use risc0_zkvm::guest::env;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};

risc0_zkvm::guest::entry!(main);

fn main() {
    // Read the public key from the host (32 bytes)
    let mut public_key_bytes = [0u8; 32];
    env::read_slice(&mut public_key_bytes);
    
    // Read the message length
    let message_len: u32 = env::read();
    
    // Read the message
    let message = if message_len > 0 {
        let mut msg = vec![0u8; message_len as usize];
        env::read_slice(&mut msg);
        msg
    } else {
        vec![]
    };
    
    // Read the signature from the host (64 bytes)
    let mut signature_bytes = [0u8; 64];
    env::read_slice(&mut signature_bytes);
    
    // Parse the public key (RISC Zero's fork uses VerifyingKey)
    let public_key = match VerifyingKey::from_bytes(&public_key_bytes) {
        Ok(key) => key,
        Err(_) => {
            env::commit(&false);
            return;
        }
    };
    
    // Parse the signature
    let signature = Signature::from_bytes(&signature_bytes);
    
    // Verify the signature
    let is_valid = public_key.verify(&message, &signature).is_ok();
    
    // Commit the verification result
    env::commit(&is_valid);
}
EOF

# Update the guest Cargo.toml to include ed25519-dalek
echo "Updating dependencies..."
cat > guest/Cargo.toml << 'EOF'
[package]
name = "method"
version = "0.1.0"
edition = "2021"

[workspace]

[dependencies]
risc0-zkvm = { version = "1.0", default-features = false, features = ["std"] }
# Use RISC Zero's fork of ed25519-dalek 
ed25519-dalek = { git = "https://github.com/risc0/curve25519-dalek", tag = "curve25519-4.1.2-risczero.0" }
sha2 = { git = "https://github.com/risc0/RustCrypto-hashes", tag = "sha2-v0.10.8-risczero.0" }
crypto-bigint = { git = "https://github.com/risc0/RustCrypto-crypto-bigint", tag = "v0.5.5-risczero.0" }

[patch.crates-io]
# Use RISC Zero's forked versions for zkVM compatibility
ed25519-dalek = { git = "https://github.com/risc0/curve25519-dalek", tag = "curve25519-4.1.2-risczero.0" }
sha2 = { git = "https://github.com/risc0/RustCrypto-hashes", tag = "sha2-v0.10.8-risczero.0" }
crypto-bigint = { git = "https://github.com/risc0/RustCrypto-crypto-bigint", tag = "v0.5.5-risczero.0" }

[profile.release]
opt-level = 3
lto = true
EOF

# Create the build.rs file for the methods crate to trigger guest compilation
echo "Creating build.rs for methods crate..."
cat > build.rs << 'EOF'
fn main() {
    risc0_build::embed_methods();
}
EOF

# Create a minimal lib.rs for the methods crate
echo "Creating lib.rs for methods crate..."
mkdir -p src
cat > src/lib.rs << 'EOF'
// This file is needed for the methods crate to compile
// The actual guest code is in guest/src/main.rs
// risc0_build::embed_methods() will generate the actual content
EOF

# Update methods/Cargo.toml to include risc0-build as a build dependency
echo "Updating methods/Cargo.toml with build dependencies..."
cat > Cargo.toml << 'EOF'
[package]
name = "methods"
version = "0.1.0"
edition = "2021"

[build-dependencies]
risc0-build = { version = "1.0" }

[package.metadata.risc0]
methods = ["guest"]
EOF

# Build the guest program (we're already in methods directory)
echo "Building the guest program..."
cargo build --release

# Extract the built ELF
echo "Extracting built ELF..."

# Go back to the project root where the workspace-wide target directory is
# We're in ed25519-verifier/methods, so go up one level to ed25519-verifier
cd ..

# The ELF is in a nested structure: target/riscv-guest/<host-crate>/<guest-crate>/riscv32im-risc0-zkvm-elf/release/<binary>
# For our setup:
# - host-crate = "methods" (the crate that has build.rs with embed_methods)
# - guest-crate = "method" (the guest package name)
# - binary = "method" (the binary name, same as guest crate name)
ELF_PATH="target/riscv-guest/methods/method/riscv32im-risc0-zkvm-elf/release/method"

if [ -f "$ELF_PATH" ]; then
    echo "Found ELF at: $ELF_PATH"
    cp "$ELF_PATH" ed25519_verifier.elf
else
    # Try with debug profile if release wasn't found
    ELF_PATH="target/riscv-guest/methods/method/riscv32im-risc0-zkvm-elf/debug/method"
    if [ -f "$ELF_PATH" ]; then
        echo "Found ELF at: $ELF_PATH (debug build)"
        cp "$ELF_PATH" ed25519_verifier.elf
    else
        # List what we have to debug - search for any executable in riscv-guest
        echo "Could not find ELF. Searching for it..."
        echo "Looking for executables in target/riscv-guest:"
        find target/riscv-guest -type f -executable 2>/dev/null
        
        # If still not found, exit with error
        echo "Error: Could not locate the built ELF file"
        echo "Expected location: target/riscv-guest/methods/method/riscv32im-risc0-zkvm-elf/release/method"
        exit 1
    fi
fi

if [ ! -f "ed25519_verifier.elf" ]; then
    echo "Error: Failed to extract ELF"
    exit 1
fi

# Copy the ELF to the test directory
cp ed25519_verifier.elf "$ORIGINAL_DIR/ed25519_verifier.elf"

echo "========================================"
echo "Success! Ed25519 verifier built and copied to:"
echo "  $ORIGINAL_DIR/ed25519_verifier.elf"
echo ""
echo "You can now run: uv run python test/ed25519_test.py"

# Clean up
cd "$ORIGINAL_DIR"
rm -rf "$TEMP_DIR"