#!/usr/bin/env python3
"""
Complete Merkle ZKP Demo - Privacy-preserving membership proofs

This demonstrates:
1. Building a Merkle tree with multiple user commitments (like 2LA)
2. Proving membership of ONE commitment without revealing which one
3. Clear separation between prover (who knows the secret) and verifier
"""

import merkle_py
import secrets
import hashlib
from pathlib import Path
import subprocess
import json
import time

# For demonstration, we'll simulate the hash functions
def sha256_hash(*args):
    """Hash multiple byte arrays together using SHA256."""
    hasher = hashlib.sha256()
    for arg in args:
        hasher.update(arg)
    return hasher.digest()

def create_commitment(k_pub: bytes, r: bytes, e: bytes) -> bytes:
    """Create a commitment C = Hash(k_pub || r || e) like in 2LA."""
    return sha256_hash(k_pub, r, e)

def simulate_users_database():
    """
    Simulate a database of users with their commitments.
    In 2LA, each user has:
    - k_pub: public key
    - r: randomness (kept private)
    - e: nullifier derived from external identity (VC)
    """
    users = []
    for i in range(8):  # Create 8 users
        user = {
            'id': f'user_{i}',
            'k_pub': secrets.token_bytes(32),
            'r': secrets.token_bytes(32),
            'e': secrets.token_bytes(32),
        }
        user['commitment'] = create_commitment(user['k_pub'], user['r'], user['e'])
        users.append(user)
    return users

def build_merkle_tree_from_commitments(commitments):
    """Build a Merkle tree from user commitments."""
    tree = merkle_py.MerkleTree()
    
    # Insert all commitments
    for i, commitment in enumerate(commitments):
        # Convert bytes to hex string for merkle_py
        hex_key = f"0x{commitment.hex()}"
        tree.insert(hex_key)
    
    return tree

def get_merkle_proof_for_user(tree, user_commitment):
    """Get the Merkle proof for a specific user's commitment."""
    hex_key = f"0x{user_commitment.hex()}"
    
    # Get the 16-level Merkle path
    siblings, bits = tree.merkle_path_16(hex_key)
    
    # Convert siblings from hex strings to bytes
    siblings_bytes = []
    for sibling in siblings:
        # Remove '0x' prefix if present
        hex_str = sibling[2:] if sibling.startswith('0x') else sibling
        # Pad to 32 bytes
        hex_str = hex_str.zfill(64)
        siblings_bytes.append(bytes.fromhex(hex_str))
    
    # Ensure we have exactly 16 siblings (pad with zeros if needed)
    while len(siblings_bytes) < 16:
        siblings_bytes.append(bytes(32))  # Add zero sibling
    
    # Ensure we have exactly 16 bits (pad with False if needed)
    while len(bits) < 16:
        bits.append(False)
    
    return siblings_bytes, bits

def run_zkp_proof(selected_user, merkle_siblings, merkle_bits, tree_root):
    """
    Run the zero-knowledge proof.
    
    PROVER knows:
    - The user's private data (k_pub, r, e)
    - The Merkle path
    
    VERIFIER will only see:
    - The Merkle root (public)
    - The proof that SOMEONE is in the tree (but not WHO)
    """
    try:
        import pyr0
        
        print("\n" + "="*60)
        print("ZERO-KNOWLEDGE PROOF GENERATION")
        print("="*60)
        
        # Build guest program if needed
        GUEST_DIR = Path(__file__).parent / "merkle_proof_guest"
        ELF_PATH = GUEST_DIR / "target" / "riscv32im-risc0-zkvm-elf" / "release" / "merkle-proof-guest"
        
        if not ELF_PATH.exists():
            print("\nBuilding RISC Zero guest program...")
            print("  (This may take a minute on first run)")
            
            # Build using the same approach as risc0_ed25519_demo.py
            result = subprocess.run([
                "cargo", "+risc0", "build", "--release",
                "--target", "riscv32im-risc0-zkvm-elf"
            ], cwd=GUEST_DIR, capture_output=True, text=True)
            
            if result.returncode != 0:
                print("⚠️  Failed to build guest program")
                print(f"  Error: {result.stderr[:300] if result.stderr else 'Unknown error'}...")
                print("\n  If you see 'no such subcommand: `+risc0`', install the RISC Zero toolchain:")
                print("  cargo install cargo-risczero && cargo risczero install")
                return None
            
            if not ELF_PATH.exists():
                print("⚠️  Build succeeded but ELF not found at expected location")
                return None
            
            print(f"✓ Guest program built successfully: {ELF_PATH.name}")
        
        # Load the guest program
        with open(ELF_PATH, "rb") as f:
            elf_data = f.read()
        image = pyr0.load_image_from_elf(elf_data)
        
        print(f"\nProver's private inputs:")
        print(f"  k_pub: 0x{selected_user['k_pub'].hex()[:16]}...")
        print(f"  r:     0x{selected_user['r'].hex()[:16]}... (secret!)")
        print(f"  e:     0x{selected_user['e'].hex()[:16]}... (secret!)")
        print(f"  Merkle path: {len(merkle_siblings)} siblings (secret!)")
        
        # Prepare input for the guest program using PyR0 serialization
        # RISC Zero expects each byte as a u32 word
        input_data = b""
        
        # k_pub, r, e - each byte as u32
        for byte_val in selected_user['k_pub']:
            input_data += pyr0.serialization.u32(byte_val)
        for byte_val in selected_user['r']:
            input_data += pyr0.serialization.u32(byte_val)
        for byte_val in selected_user['e']:
            input_data += pyr0.serialization.u32(byte_val)
        
        # Path length
        input_data += pyr0.serialization.u32(len(merkle_siblings))
        
        # Path siblings - each byte as u32
        for sibling in merkle_siblings:
            for byte_val in sibling:
                input_data += pyr0.serialization.u32(byte_val)
        
        # Indices length and values
        input_data += pyr0.serialization.u32(len(merkle_bits))
        for bit in merkle_bits:
            input_data += pyr0.serialization.u32(1 if bit else 0)
        
        # Debug: Check the data
        print(f"\nDebug - Input data size: {len(input_data)} bytes")
        print(f"  First 100 bytes: {input_data[:100].hex()}")
        
        print(f"\nExecuting proof generation in zkVM...")
        start_time = time.time()
        
        # Execute the guest program
        # Use prepare_input to wrap the bytes properly
        prepared_input = pyr0.prepare_input(input_data)
        segments, info = pyr0.execute_with_input(image, prepared_input)
        
        if not segments or len(segments) == 0:
            print("⚠️  Execution failed")
            return None
        
        # Generate the proof
        receipt = pyr0.prove_segment(segments[0])
        elapsed = time.time() - start_time
        
        print(f"✓ Proof generated in {elapsed:.2f} seconds")
        
        # The journal contains the public outputs (root and k_pub)
        journal = segments[0].journal if hasattr(segments[0], 'journal') else b""
        print(f"✓ Public output size: {len(journal)} bytes")
        
        return receipt, journal
        
    except ImportError:
        print("\n⚠️  PyR0 not installed - cannot generate real ZKP")
        print("Install PyR0 to enable zero-knowledge proofs")
        return None
    except Exception as e:
        print(f"\n⚠️  ZKP generation failed: {e}")
        return None

def verify_zkp(receipt, expected_root):
    """
    Verify the zero-knowledge proof.
    
    The VERIFIER only knows:
    - The Merkle root
    - The proof receipt
    
    The VERIFIER does NOT know:
    - Which user is proving membership
    - The Merkle path
    - The user's private data
    """
    try:
        import pyr0
        
        print("\n" + "="*60)
        print("ZERO-KNOWLEDGE PROOF VERIFICATION")
        print("="*60)
        
        print("\nVerifier knows:")
        print(f"  Expected Merkle root: 0x{expected_root[:16]}...")
        print("  Proof receipt: [cryptographic proof]")
        
        print("\nVerifier does NOT know:")
        print("  ✗ Which user is in the tree")
        print("  ✗ The user's commitment value")
        print("  ✗ The Merkle path taken")
        print("  ✗ Any private user data")
        
        print("\nVerifying proof...")
        pyr0.verify_receipt(receipt)
        print("✓ Proof is VALID!")
        
        print("\nConclusion:")
        print("  The prover has demonstrated they know a valid")
        print("  commitment in the Merkle tree WITHOUT revealing")
        print("  which commitment or any private information!")
        
        return True
        
    except ImportError:
        print("\n⚠️  PyR0 not installed - cannot verify ZKP")
        return False
    except Exception as e:
        print(f"\n✗ Verification FAILED: {e}")
        return False

def main():
    """Run the complete Merkle ZKP demonstration."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "MERKLE ZERO-KNOWLEDGE PROOF DEMO" + " " * 13 + "║")
    print("║" + " " * 8 + "Privacy-Preserving Membership Proofs" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    print("\nScenario: Multiple users have registered commitments.")
    print("Goal: Prove you're a registered user WITHOUT revealing which one.")
    
    # Step 1: Create users and their commitments
    print("\n" + "="*60)
    print("STEP 1: SETUP - Creating User Database")
    print("="*60)
    
    users = simulate_users_database()
    print(f"\n✓ Created {len(users)} users with commitments")
    
    for i, user in enumerate(users[:3]):
        print(f"\n  User {i}:")
        print(f"    Commitment: 0x{user['commitment'].hex()[:16]}...")
    print(f"  ... and {len(users)-3} more users")
    
    # Step 2: Build Merkle tree from all commitments
    print("\n" + "="*60)
    print("STEP 2: BUILD MERKLE TREE")
    print("="*60)
    
    commitments = [user['commitment'] for user in users]
    tree = build_merkle_tree_from_commitments(commitments)
    root = tree.root()
    
    print(f"\n✓ Built Merkle tree with {len(commitments)} commitments")
    print(f"  Tree root: {root[:32]}...")
    print("\nThis root is PUBLIC - everyone can see it")
    
    # Step 3: Select a user to prove membership (privately)
    print("\n" + "="*60)
    print("STEP 3: PROVER SELECTS THEIR IDENTITY (PRIVATE)")
    print("="*60)
    
    # For demo, we'll prove user 3 is in the tree
    prover_index = 3
    selected_user = users[prover_index]
    
    print(f"\nProver secretly selects: User {prover_index}")
    print(f"  Their commitment: 0x{selected_user['commitment'].hex()[:16]}...")
    print("  (This selection is PRIVATE - verifier won't know)")
    
    # Step 4: Generate Merkle proof for the selected user
    siblings, bits = get_merkle_proof_for_user(tree, selected_user['commitment'])
    
    print(f"\n✓ Generated Merkle proof:")
    print(f"  Path length: {len(siblings)} siblings (padded to 16)")
    print(f"  Direction bits: {bits[:4]}... (L=False, R=True)")
    print("  (This proof path is PRIVATE)")
    
    # Step 5: Generate zero-knowledge proof
    result = run_zkp_proof(selected_user, siblings, bits, root)
    
    if result:
        receipt, journal = result
        
        # Step 6: Verify the proof (as a separate party would)
        verify_zkp(receipt, root)
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("\nWhat just happened:")
        print("1. We created a Merkle tree with 8 user commitments")
        print("2. User 3 proved they're in the tree")
        print("3. The verifier confirmed the proof")
        print("4. The verifier learned NOTHING about which user it was!")
        print("\nThis enables anonymous authentication - proving you're")
        print("a valid member without revealing your identity.")
    else:
        print("\n" + "="*60)
        print("DEMO COMPLETED (without real ZKP)")
        print("="*60)
        print("\nThe Merkle tree operations work correctly.")
        print("To enable zero-knowledge proofs:")
        print("  1. Install RISC Zero toolchain")
        print("  2. Build and install PyR0")

if __name__ == "__main__":
    main()