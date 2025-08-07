#!/usr/bin/env python3
"""
Extract the Ed25519 verifier ELF from a RISC Zero build.

When RISC Zero builds a guest program, it embeds the ELF as a byte array
in a generated methods.rs file. This script extracts that ELF.
"""

import os
import re
import sys
from pathlib import Path

def find_methods_rs(search_dir="."):
    """Find the generated methods.rs file."""
    for root, dirs, files in os.walk(search_dir):
        if "methods.rs" in files:
            return os.path.join(root, "methods.rs")
    return None

def extract_elf_from_methods_rs(methods_rs_path):
    """Extract the ELF bytes from methods.rs."""
    with open(methods_rs_path, 'r') as f:
        content = f.read()
    
    # Look for the ELF constant - it's usually named METHOD_ELF or similar
    # Pattern: pub const METHOD_ELF: &[u8] = &[...];
    pattern = r'pub const \w+_ELF: &\[u8\] = &\[([\d\s,]+)\];'
    match = re.search(pattern, content)
    
    if not match:
        # Try alternative pattern for included bytes
        pattern = r'pub const \w+_ELF: &\[u8\] = include_bytes!\("([^"]+)"\);'
        match = re.search(pattern, content)
        if match:
            # The ELF is included from a file
            elf_path = match.group(1)
            # Make path relative to methods.rs location
            base_dir = os.path.dirname(methods_rs_path)
            full_elf_path = os.path.join(base_dir, elf_path)
            if os.path.exists(full_elf_path):
                return full_elf_path, None
        return None, None
    
    # Parse the byte array
    bytes_str = match.group(1)
    bytes_list = [int(b.strip()) for b in bytes_str.split(',') if b.strip()]
    return None, bytes(bytes_list)

def find_built_elf(build_dir):
    """Try to find the built ELF directly."""
    # Common locations for the ELF
    possible_paths = [
        "target/riscv-guest/riscv32im-risc0-zkvm-elf/release/method",
        "target/riscv32im-risc0-zkvm-elf/release/method",
        "methods/guest/target/riscv32im-risc0-zkvm-elf/release/method",
    ]
    
    for path in possible_paths:
        full_path = os.path.join(build_dir, path)
        if os.path.exists(full_path):
            return full_path
    
    # Search for any ELF file
    for root, dirs, files in os.walk(os.path.join(build_dir, "target")):
        for file in files:
            if file == "method" and "riscv32im" in root:
                return os.path.join(root, file)
    
    return None

def main():
    if len(sys.argv) > 1:
        build_dir = sys.argv[1]
    else:
        build_dir = "."
    
    # First try to find the ELF directly
    elf_path = find_built_elf(build_dir)
    if elf_path:
        print(f"Found ELF at: {elf_path}")
        with open(elf_path, 'rb') as f:
            elf_data = f.read()
        
        output_path = "ed25519_verifier.elf"
        with open(output_path, 'wb') as f:
            f.write(elf_data)
        print(f"Copied ELF to: {output_path}")
        return 0
    
    # If not found, try to extract from methods.rs
    methods_rs = find_methods_rs(build_dir)
    if not methods_rs:
        print("Error: Could not find methods.rs or built ELF")
        return 1
    
    print(f"Found methods.rs at: {methods_rs}")
    
    elf_file_path, elf_bytes = extract_elf_from_methods_rs(methods_rs)
    
    if elf_file_path:
        print(f"ELF is at: {elf_file_path}")
        with open(elf_file_path, 'rb') as f:
            elf_data = f.read()
    elif elf_bytes:
        print(f"Extracted {len(elf_bytes)} bytes of ELF data")
        elf_data = elf_bytes
    else:
        print("Error: Could not extract ELF from methods.rs")
        return 1
    
    # Write the ELF to a file
    output_path = "ed25519_verifier.elf"
    with open(output_path, 'wb') as f:
        f.write(elf_data)
    
    print(f"Written ELF to: {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())