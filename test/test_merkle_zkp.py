#!/usr/bin/env python3
"""
Simple test of the Merkle ZKP functionality.
Run this to verify the integration works.
"""

import sys
from pathlib import Path

# Add parent directory to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_merkle_tree():
    """Test that merkle_py works."""
    try:
        import merkle_py
        print("✓ merkle_py module loaded")
        
        # Create a tree and add some values
        tree = merkle_py.MerkleTree()
        tree.insert("0x0000000000000000000000000000000000000000000000000000000000000001")
        tree.insert("0x0000000000000000000000000000000000000000000000000000000000000002")
        
        root = tree.root()
        print(f"✓ Merkle tree works, root: {root[:32]}...")
        
        # Get a proof
        siblings, bits = tree.merkle_path_16("0x0000000000000000000000000000000000000000000000000000000000000001")
        print(f"✓ Generated proof with {len(siblings)} siblings")
        
        return True
    except Exception as e:
        print(f"✗ Merkle tree test failed: {e}")
        return False

def test_pyr0():
    """Test that PyR0 works."""
    try:
        import pyr0
        print("✓ PyR0 module loaded")
        
        # Test serialization functions
        test_bytes = b"hello"
        serialized = pyr0.serialization.vec_u8(test_bytes)
        print(f"✓ Serialization works, serialized {len(test_bytes)} bytes to {len(serialized)} bytes")
        
        return True
    except Exception as e:
        print(f"✗ PyR0 test failed: {e}")
        return False

def test_zkp_demo():
    """Test the full ZKP demo."""
    try:
        print("\n" + "="*50)
        print("Testing full Merkle ZKP demo...")
        print("="*50)
        
        # Import the demo from the demo directory
        import sys
        from pathlib import Path
        demo_path = Path(__file__).parent.parent / "demo"
        sys.path.insert(0, str(demo_path))
        
        from merkle_zkp_demo import main
        main()
        
        return True
    except Exception as e:
        print(f"✗ ZKP demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Merkle ZKP Components")
    print("="*50)
    
    # Test each component
    merkle_ok = test_merkle_tree()
    pyr0_ok = test_pyr0()
    
    if merkle_ok and pyr0_ok:
        print("\n✓ All components working, running full demo...\n")
        test_zkp_demo()
    else:
        print("\n⚠️  Some components not working")
        print("Make sure PyR0 and merkle_py are installed")