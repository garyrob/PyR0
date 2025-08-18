#!/usr/bin/env python3
"""
Test the Receipt API improvements:
- Python-friendly properties (journal_bytes, journal_hex, journal_text)
- ExitStatus with structured exit information
- Claimed vs trusted image ID separation
- New verification methods (verify_hex, verify_bytes, verify_integrity)
- Receipt serialization
"""

import sys
import os
from pathlib import Path

def test_receipt_api():
    """Test all Receipt API improvements."""
    print("Testing Receipt API")
    print("=" * 60)
    
    test_passed = True
    
    try:
        import pyr0
        from pyr0 import serialization
        
        # Build test guest if needed
        GUEST_DIR = Path(__file__).parent / "demo" / "ed25519_demo_guest"
        
        try:
            print("\nBuilding test guest program...")
            elf_path = pyr0.build_guest(GUEST_DIR, "ed25519-guest-input")
            
            with open(elf_path, "rb") as f:
                elf_data = f.read()
        except (pyr0.GuestBuildFailedError, pyr0.ElfNotFoundError) as e:
            print(f"✗ Failed to build guest: {e}")
            return False
        
        image = pyr0.load_image(elf_data)
        trusted_image_id = image.id.hex()
        
        # Create a receipt
        print("\n1. Creating test receipt...")
        PUBLIC_KEY = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
        VALID_SIG = "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
        MESSAGE = ""
        
        pk_bytes = bytes.fromhex(PUBLIC_KEY)
        sig_bytes = bytes.fromhex(VALID_SIG)
        msg_bytes = MESSAGE.encode('utf-8')
        input_data = serialization.ed25519_input(pk_bytes, sig_bytes, msg_bytes)
        
        receipt = pyr0.prove(image, input_data)
        print("   ✓ Receipt created")
        
        # Test 2: Journal properties
        print("\n2. Testing journal properties...")
        
        # journal_bytes
        journal_bytes = receipt.journal_bytes
        if not isinstance(journal_bytes, bytes):
            print(f"   ✗ journal_bytes should be bytes, got {type(journal_bytes)}")
            test_passed = False
        else:
            print(f"   ✓ journal_bytes: {len(journal_bytes)} bytes")
        
        # journal_hex
        journal_hex = receipt.journal_hex
        if not isinstance(journal_hex, str):
            print(f"   ✗ journal_hex should be str, got {type(journal_hex)}")
            test_passed = False
        elif len(journal_hex) != len(journal_bytes) * 2:
            print(f"   ✗ journal_hex wrong length: {len(journal_hex)} != {len(journal_bytes) * 2}")
            test_passed = False
        else:
            print(f"   ✓ journal_hex: {len(journal_hex)} chars")
        
        # Verify hex matches bytes
        if bytes.fromhex(journal_hex) != journal_bytes:
            print("   ✗ journal_hex doesn't match journal_bytes!")
            test_passed = False
        else:
            print("   ✓ journal_hex matches journal_bytes")
        
        # journal_text
        journal_text = receipt.journal_text
        if journal_text is not None and not isinstance(journal_text, str):
            print(f"   ✗ journal_text should be str or None, got {type(journal_text)}")
            test_passed = False
        else:
            print(f"   ✓ journal_text: {type(journal_text).__name__}")
        
        # journal_len
        if receipt.journal_len != len(journal_bytes):
            print(f"   ✗ journal_len mismatch: {receipt.journal_len} != {len(journal_bytes)}")
            test_passed = False
        else:
            print(f"   ✓ journal_len: {receipt.journal_len}")
        
        # Legacy journal property
        if receipt.journal != journal_bytes:
            print("   ✗ Legacy journal property doesn't match journal_bytes")
            test_passed = False
        else:
            print("   ✓ Legacy journal property works")
        
        # Test 3: ExitStatus
        print("\n3. Testing ExitStatus...")
        exit_status = receipt.exit
        
        if not hasattr(exit_status, 'kind'):
            print("   ✗ ExitStatus missing 'kind'")
            test_passed = False
        else:
            print(f"   ✓ exit.kind: {exit_status.kind}")
        
        if not hasattr(exit_status, 'user_code'):
            print("   ✗ ExitStatus missing 'user_code'")
            test_passed = False
        else:
            print(f"   ✓ exit.user_code: {exit_status.user_code}")
        
        if not hasattr(exit_status, 'ok'):
            print("   ✗ ExitStatus missing 'ok'")
            test_passed = False
        else:
            print(f"   ✓ exit.ok: {exit_status.ok}")
        
        # Test ExitKind enum values
        print("\n4. Testing ExitKind enum...")
        if not hasattr(pyr0, 'ExitKind'):
            print("   ✗ ExitKind not exported")
            test_passed = False
        else:
            print(f"   ✓ ExitKind.HALTED: {pyr0.ExitKind.HALTED}")
            print(f"   ✓ ExitKind.PAUSED: {pyr0.ExitKind.PAUSED}")
            print(f"   ✓ ExitKind.SYSTEM_SPLIT: {pyr0.ExitKind.SYSTEM_SPLIT}")
            print(f"   ✓ ExitKind.SESSION_LIMIT: {pyr0.ExitKind.SESSION_LIMIT}")
        
        # For successful execution, should be HALTED(0)
        if exit_status.kind != pyr0.ExitKind.HALTED:
            print(f"   ✗ Expected HALTED for successful execution")
            test_passed = False
        if exit_status.user_code != 0:
            print(f"   ✗ Expected user_code=0 for success")
            test_passed = False
        if not exit_status.ok:
            print(f"   ✗ Expected ok=True for HALTED(0)")
            test_passed = False
        
        # Legacy exit_code property
        if receipt.exit_code != 0:
            print(f"   ✗ Legacy exit_code should be 0, got {receipt.exit_code}")
            test_passed = False
        else:
            print("   ✓ Legacy exit_code property works")
        
        # Test 5: Claimed image ID
        print("\n5. Testing claimed image ID...")
        
        claimed_hex = receipt.claimed_image_id_hex
        if not isinstance(claimed_hex, str) or len(claimed_hex) != 64:
            print(f"   ✗ claimed_image_id_hex wrong format")
            test_passed = False
        else:
            print(f"   ✓ claimed_image_id_hex: {claimed_hex[:16]}...")
        
        claimed_bytes = receipt.claimed_image_id_bytes
        if not isinstance(claimed_bytes, bytes) or len(claimed_bytes) != 32:
            print(f"   ✗ claimed_image_id_bytes wrong format")
            test_passed = False
        else:
            print(f"   ✓ claimed_image_id_bytes: {len(claimed_bytes)} bytes")
        
        # Verify they match
        if claimed_hex != claimed_bytes.hex():
            print("   ✗ Hex and bytes don't match!")
            test_passed = False
        else:
            print("   ✓ Hex and bytes match")
        
        # Should match trusted ID for valid receipt
        if claimed_hex != trusted_image_id:
            print("   ✗ Claimed ID doesn't match trusted ID (unexpected)")
            test_passed = False
        else:
            print("   ✓ Claimed ID matches trusted ID (as expected)")
        
        # Legacy program_id property
        if receipt.program_id != claimed_bytes:
            print("   ✗ Legacy program_id doesn't match claimed_image_id_bytes")
            test_passed = False
        else:
            print("   ✓ Legacy program_id property works")
        
        # Test 6: Verification methods
        print("\n6. Testing verification methods...")
        
        # verify_hex with lowercase
        try:
            receipt.verify_hex(trusted_image_id.lower())
            print("   ✓ verify_hex(lowercase) succeeded")
        except Exception as e:
            print(f"   ✗ verify_hex(lowercase) failed: {e}")
            test_passed = False
        
        # verify_hex with uppercase
        try:
            receipt.verify_hex(trusted_image_id.upper())
            print("   ✓ verify_hex(uppercase) succeeded")
        except Exception as e:
            print(f"   ✗ verify_hex(uppercase) failed: {e}")
            test_passed = False
        
        # verify_hex with 0x prefix
        try:
            receipt.verify_hex(f"0x{trusted_image_id}")
            print("   ✓ verify_hex('0x' prefix) succeeded")
        except Exception as e:
            print(f"   ✗ verify_hex('0x' prefix) failed: {e}")
            test_passed = False
        
        # verify_hex with 0X prefix
        try:
            receipt.verify_hex(f"0X{trusted_image_id}")
            print("   ✓ verify_hex('0X' prefix) succeeded")
        except Exception as e:
            print(f"   ✗ verify_hex('0X' prefix) failed: {e}")
            test_passed = False
        
        # verify_bytes
        try:
            receipt.verify_bytes(bytes.fromhex(trusted_image_id))
            print("   ✓ verify_bytes succeeded")
        except Exception as e:
            print(f"   ✗ verify_bytes failed: {e}")
            test_passed = False
        
        # verify_integrity
        try:
            receipt.verify_integrity()
            print("   ✓ verify_integrity succeeded")
        except Exception as e:
            print(f"   ✗ verify_integrity failed: {e}")
            test_passed = False
        
        # Test wrong ID should fail
        wrong_id = "0" * 64
        try:
            receipt.verify_hex(wrong_id)
            print("   ✗ verify_hex should fail with wrong ID!")
            test_passed = False
        except Exception:
            print("   ✓ verify_hex correctly rejected wrong ID")
        
        try:
            receipt.verify_bytes(bytes(32))
            print("   ✗ verify_bytes should fail with wrong ID!")
            test_passed = False
        except Exception:
            print("   ✓ verify_bytes correctly rejected wrong ID")
        
        # Legacy verify method
        try:
            receipt.verify(image.id)
            print("   ✓ Legacy verify() method works")
        except Exception as e:
            print(f"   ✗ Legacy verify() failed: {e}")
            test_passed = False
        
        # Test 7: Seal size
        print("\n7. Testing seal_size...")
        seal_size = receipt.seal_size
        if not isinstance(seal_size, int) or seal_size <= 0:
            print(f"   ✗ seal_size invalid: {seal_size}")
            test_passed = False
        else:
            print(f"   ✓ seal_size: {seal_size} bytes")
        
        # Test 8: Receipt serialization
        print("\n8. Testing receipt serialization...")
        try:
            receipt_bytes = receipt.to_bytes()
            if not isinstance(receipt_bytes, bytes) or len(receipt_bytes) == 0:
                print(f"   ✗ to_bytes() failed")
                test_passed = False
            else:
                print(f"   ✓ Serialized to {len(receipt_bytes)} bytes")
            
            receipt2 = pyr0.Receipt.from_bytes(receipt_bytes)
            print("   ✓ Deserialized successfully")
            
            # Verify key properties match
            if receipt2.journal_bytes != receipt.journal_bytes:
                print("   ✗ Journal doesn't match after round-trip")
                test_passed = False
            else:
                print("   ✓ Journal matches")
            
            if receipt2.claimed_image_id_hex != receipt.claimed_image_id_hex:
                print("   ✗ Image ID doesn't match after round-trip")
                test_passed = False
            else:
                print("   ✓ Image ID matches")
            
            if receipt2.exit.kind != receipt.exit.kind:
                print("   ✗ Exit status doesn't match after round-trip")
                test_passed = False
            else:
                print("   ✓ Exit status matches")
                
        except Exception as e:
            print(f"   ✗ Serialization failed: {e}")
            test_passed = False
        
        # Test 9: __repr__
        print("\n9. Testing __repr__...")
        repr_str = repr(receipt)
        if "Receipt(" not in repr_str:
            print(f"   ✗ Receipt.__repr__ format wrong: {repr_str}")
            test_passed = False
        elif "journal_len=" not in repr_str:
            print(f"   ✗ Receipt.__repr__ missing journal_len: {repr_str}")
            test_passed = False
        elif "image_id=" not in repr_str:
            print(f"   ✗ Receipt.__repr__ missing image_id: {repr_str}")
            test_passed = False
        else:
            print(f"   ✓ Receipt.__repr__: {repr_str}")
        
        exit_repr = repr(exit_status)
        if "ExitStatus(" not in exit_repr:
            print(f"   ✗ ExitStatus.__repr__ format wrong: {exit_repr}")
            test_passed = False
        else:
            print(f"   ✓ ExitStatus.__repr__: {exit_repr}")
        
        # Test 10: compute_image_id_hex
        print("\n10. Testing compute_image_id_hex...")
        computed_id = pyr0.compute_image_id_hex(elf_data)
        if not isinstance(computed_id, str) or len(computed_id) != 64:
            print(f"   ✗ compute_image_id_hex wrong format")
            test_passed = False
        else:
            print(f"   ✓ compute_image_id_hex: {computed_id[:16]}...")
        
        if computed_id != trusted_image_id:
            print(f"   ✗ Computed ID doesn't match image.id")
            test_passed = False
        else:
            print("   ✓ Computed ID matches image.id")
        
        return test_passed
        
    except ImportError as e:
        print(f"\n✗ Failed to import PyR0: {e}")
        print("  Please rebuild: uv tool run maturin build --release")
        print("  Then install: uv pip install --force-reinstall target/wheels/PyR0-*.whl")
        return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Receipt API tests."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "Receipt API Test Suite" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    
    test_passed = test_receipt_api()
    
    print("\n" + "=" * 60)
    if test_passed:
        print("✅ All Receipt API tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())