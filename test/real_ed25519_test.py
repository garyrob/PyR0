#!/usr/bin/env python3
"""Final test with proper RISC Zero serialization"""

import os
import sys
import time
import subprocess
from pathlib import Path

os.environ['RISC0_DEV_MODE'] = '0'

# Fresh import
import pyr0

# Constants
GUEST_DIR = Path(__file__).parent / "real_ed25519_test_guest"
ELF_PATH = GUEST_DIR / "target" / "riscv32im-risc0-zkvm-elf" / "release" / "ed25519-guest-input"
PUBLIC_KEY = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
VALID_SIG = "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
INVALID_SIG = "3b41da0837e8f4e7b1ba8d9e0db233a22a5764c84e8870c049e7e210c512a4532dbab6222d5e98dd50fe0fb186c039fe9a0387bf43de1fbf655c101db2540b06"
MESSAGE = ""

print(f"Using pyr0 with serialize_for_guest: {hasattr(pyr0, 'serialize_for_guest')}")

# Delete existing ELF to ensure fresh build
if ELF_PATH.exists():
    print(f"\nDeleting existing ELF at: {ELF_PATH}")
    os.remove(ELF_PATH)
    if ELF_PATH.exists():
        print("❌ Failed to delete ELF file!")
        sys.exit(1)
    print("✓ ELF deleted successfully")
else:
    print(f"\nNo existing ELF found at: {ELF_PATH}")

# Build the guest
print("\nBuilding guest program...")
result = subprocess.run([
    "cargo", "+risc0", "build", "--release",
    "--target", "riscv32im-risc0-zkvm-elf"
], cwd=GUEST_DIR)

if result.returncode != 0:
    print("❌ Build failed!")
    sys.exit(1)

# Verify ELF was created
if not ELF_PATH.exists():
    print(f"❌ ELF not found after build at: {ELF_PATH}")
    sys.exit(1)

print(f"✓ ELF built successfully: {ELF_PATH}")
print(f"  Size: {os.path.getsize(ELF_PATH):,} bytes")

# Load the ELF
with open(ELF_PATH, "rb") as f:
    elf_data = f.read()
image = pyr0.load_image_from_elf(elf_data)
print("✓ ELF loaded into image")

# Test with valid signature
print("\n=== Test 1: Valid Signature ===")
pk_bytes = bytes.fromhex(PUBLIC_KEY)
sig_bytes = bytes.fromhex(VALID_SIG)
msg_bytes = MESSAGE.encode('utf-8')

# Use RISC Zero's proper serialization
input_data = pyr0.serialize_for_guest([
    list(pk_bytes),
    list(sig_bytes),
    list(msg_bytes)
])

print(f"Input size: {len(input_data)} bytes")
print("Executing...")

segments, info = pyr0.execute_with_input(image, input_data)
journal = info.get_journal()

print(f"Journal: {len(journal)} bytes")
print(f"First 10 bytes: {journal[:10]}")

if len(journal) >= 4 and journal[0] == 99:
    print("✓ Guest started (marker 99)")
    # The guest is committing u8 values, but journal stores them as u32 words
    # Each commit becomes 4 bytes in the journal
    if len(journal) >= 16:
        # Read as u32 values (little-endian)
        import struct
        marker = struct.unpack('<I', journal[0:4])[0]  # Should be 99
        pk_size = struct.unpack('<I', journal[4:8])[0]  # Should be 32
        sig_size = struct.unpack('<I', journal[8:12])[0]  # Should be 64
        msg_size = struct.unpack('<I', journal[12:16])[0]  # Should be 0
        print(f"Vector sizes: pk={pk_size}, sig={sig_size}, msg={msg_size}")

        if len(journal) >= 20:
            # The result byte is at position 16
            result = struct.unpack('<I', journal[16:20])[0]
            if result == 1:
                print("✅ Signature VALID - Test PASSED")
            elif result == 0:
                print("❌ Signature reported as INVALID - Test FAILED")
            elif result == 200:
                print("❌ Size mismatch error")
            elif result == 201:
                print("❌ Invalid public key error")
            else:
                print(f"Unexpected result: {result}")

# Generate proof
print("\nGenerating proof...")
start = time.time()
receipt = pyr0.prove_segment(segments[0])
proof_time = time.time() - start
print(f"Proof generated in {proof_time:.2f}s")

# Verify
pyr0.verify_receipt(receipt)
print("✓ Proof verified")

# Test with invalid signature
print("\n=== Test 2: Invalid Signature ===")
sig_bytes = bytes.fromhex(INVALID_SIG)

input_data = pyr0.serialize_for_guest([
    list(pk_bytes),
    list(sig_bytes),
    list(msg_bytes)
])

segments, info = pyr0.execute_with_input(image, input_data)
journal = info.get_journal()

print(f"Journal: {len(journal)} bytes")
if len(journal) >= 20 and journal[0] == 99:
    import struct
    result = struct.unpack('<I', journal[16:20])[0]
    if result == 0:
        print("✅ Signature INVALID - Test PASSED")
    elif result == 1:
        print("❌ Signature reported as VALID - Test FAILED")

print("\n=== Summary ===")
print("If both tests passed, the zkVM correctly validates Ed25519 signatures!")
print("These are real cryptographic proofs in production mode.")