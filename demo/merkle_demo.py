#!/usr/bin/env python3
"""
Demo of sparse Merkle tree with Poseidon hash for zero-knowledge proofs.

This demonstrates a Python interface to a sparse Merkle tree that uses
Poseidon hash over BN254, compatible with Noir/Barretenberg ZK circuits.
"""

import sys
import merkle_py

def test_basic_operations():
    """Test basic Merkle tree operations."""
    print("\n" + "="*60)
    print("TEST 1: Basic Sparse Merkle Tree Operations")
    print("="*60)
    
    # Create a new tree
    tree = merkle_py.MerkleTree()
    initial_root = tree.root()
    print(f"\n1. Created empty sparse Merkle tree")
    print(f"   Initial root (all zeros): {initial_root[:16]}...")
    
    # Insert some keys
    print("\n2. Inserting keys into the tree...")
    keys = [
        "0x0000000000000000000000000000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000000000000000000000000000002",
        "0x0000000000000000000000000000000000000000000000000000000000000003",
    ]
    
    for i, key in enumerate(keys, 1):
        tree.insert(key)
        new_root = tree.root()
        print(f"   Key {i}: {key[:10]}...{key[-6:]}")
        print(f"   New root: {new_root[:16]}...")
    
    # Check membership
    print("\n3. Testing membership checks...")
    for key in keys:
        is_member = tree.contains(key)
        print(f"   Key {key[-6:]}: {'✓ Present' if is_member else '✗ Not found'}")
        assert is_member, f"Key {key} should be in tree"
    
    test_key = "0x0000000000000000000000000000000000000000000000000000000000000004"
    is_member = tree.contains(test_key)
    print(f"   Key {test_key[-6:]}: {'✓ Present' if is_member else '✗ Not found (expected)'}")
    assert not is_member, "Non-existent key should not be in tree"
    
    # Generate Merkle path for first key
    print("\n4. Generating 16-level Merkle proof for key verification...")
    siblings, bits = tree.merkle_path_16(keys[0])
    print(f"   Target key: {keys[0]}")
    print(f"   Path length: {len(siblings)} siblings (for 16-level tree)")
    print(f"   First 3 siblings:")
    for i, sib in enumerate(siblings[:3]):
        print(f"     Level {i}: {sib[:16]}...")
    print(f"   Direction bits (L=0, R=1): {bits}")
    print(f"   This proof can verify membership in a tree with up to 2^16 = 65,536 leaves")
    
    return tree


def test_poseidon_hash():
    """Test Poseidon hash function."""
    print("\n" + "="*60)
    print("TEST 2: Poseidon Hash Function (BN254 Field)")
    print("="*60)
    
    print("\n1. Hashing two field elements together...")
    # Hash two field elements
    inputs = [
        "0x0000000000000000000000000000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000000000000000000000000000002",
    ]
    
    print(f"   Input 1: {inputs[0]}")
    print(f"   Input 2: {inputs[1]}")
    
    result = merkle_py.poseidon_hash(inputs)
    print(f"   Result:  0x{result.hex()}")
    print(f"   (This is a 256-bit hash in the BN254 field)")
    
    # Test with bytes input
    print("\n2. Testing with raw bytes input...")
    inputs_bytes = [
        bytes.fromhex("01" * 32),  # 32 bytes of 0x01
        bytes.fromhex("02" * 32),  # 32 bytes of 0x02
    ]
    print(f"   Input 1: 32 bytes of 0x01")
    print(f"   Input 2: 32 bytes of 0x02")
    
    result2 = merkle_py.poseidon_hash(inputs_bytes)
    print(f"   Result:  0x{result2.hex()[:32]}...")
    
    print("\n3. Key properties of Poseidon hash:")
    print("   - Optimized for zero-knowledge proof circuits")
    print("   - Works over BN254 elliptic curve field")
    print("   - Compatible with Noir/Barretenberg circuits")
    print("   - Much more efficient than SHA256 in ZK circuits")

def test_batch_operations():
    """Test batch insertions."""
    print("\n" + "="*60)
    print("TEST 3: Batch Operations for Efficiency")
    print("="*60)
    
    tree = merkle_py.MerkleTree()
    
    print("\n1. Creating 10 test keys...")
    # Batch insert multiple keys
    keys = [f"0x{i:064x}" for i in range(10)]
    for i, key in enumerate(keys[:3]):
        print(f"   Key {i}: {key[:10]}...{key[-6:]}")
    print(f"   ... and {len(keys)-3} more keys")
    
    print("\n2. Performing batch insertion...")
    import time
    start = time.time()
    tree.batch_insert(keys)
    elapsed = time.time() - start
    
    print(f"   ✓ Inserted {len(keys)} keys in {elapsed:.4f} seconds")
    print(f"   Final tree root: {tree.root()[:32]}...")
    
    # Verify all keys are present
    print("\n3. Verifying all keys are present...")
    for i, key in enumerate(keys):
        is_present = tree.contains(key)
        assert is_present, f"Key {key} should be in tree"
    print(f"   ✓ All {len(keys)} keys verified present in tree")
    
    print("\n4. Performance benefits of batch operations:")
    print("   - Single write lock acquisition for all insertions")
    print("   - More efficient tree updates")
    print("   - Better for bulk data loading")

def main():
    """Run all tests."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "MERKLE TREE TEST SUITE" + " " * 21 + "║")
    print("║" + " " * 10 + "Sparse Merkle Tree with Poseidon Hash" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    
    print("\nThis test suite demonstrates a sparse Merkle tree implementation")
    print("compatible with zero-knowledge proof circuits (Noir/Barretenberg).")
    
    try:
        tree = test_basic_operations()
        test_poseidon_hash()
        test_batch_operations()
        
        print("\n" + "╔" + "=" * 58 + "╗")
        print("║" + " " * 20 + "ALL TESTS PASSED ✅" + " " * 19 + "║")
        print("╚" + "=" * 58 + "╝")
        
        print("\nThis implementation provides:")
        print("  • Sparse Merkle tree supporting 2^256 keys")
        print("  • Poseidon hash function over BN254 field")
        print("  • 16-level Merkle proofs for ZK circuits")
        print("  • Python interface via PyO3 bindings")
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())