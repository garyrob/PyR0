#!/usr/bin/env python3
"""
Test the build_guest functionality.
"""

import sys
import os
import time
from pathlib import Path
import shutil

def test_build_guest():
    """Test build_guest function."""
    print("Testing build_guest functionality")
    print("=" * 60)
    
    test_passed = True
    
    try:
        import pyr0
        
        # Test 1: Build a valid guest (always rebuilds)
        print("\n1. Testing build_guest with valid guest directory...")
        guest_dir = Path("demo/ed25519_demo_guest")
        
        try:
            # Always rebuilds from scratch
            start_time = time.time()
            elf_path = pyr0.build_guest(guest_dir, "ed25519-guest-input")
            build_time = time.time() - start_time
            print(f"   ✓ Built guest at: {elf_path}")
            print(f"   ⏱ Build time: {build_time:.2f} seconds")
            
            # Check the file exists
            if not elf_path.exists():
                print(f"   ✗ ELF path returned but file doesn't exist!")
                test_passed = False
            else:
                size = os.path.getsize(elf_path)
                print(f"   ✓ ELF exists, size: {size:,} bytes")
        except Exception as e:
            print(f"   ✗ Failed to build guest: {e}")
            test_passed = False
        
        # Test 2: Build again (should rebuild every time)
        print("\n2. Testing build_guest rebuilds every time...")
        try:
            start_time = time.time()
            elf_path2 = pyr0.build_guest(guest_dir, "ed25519-guest-input")
            build_time = time.time() - start_time
            print(f"   ✓ Rebuilt guest at: {elf_path2}")
            print(f"   ⏱ Build time: {build_time:.2f} seconds")
            
            # Check paths match
            if elf_path != elf_path2:
                print(f"   ✗ Path changed on rebuild: {elf_path} != {elf_path2}")
                test_passed = False
            else:
                print(f"   ✓ Path consistency verified")
        except Exception as e:
            print(f"   ✗ Failed to rebuild guest: {e}")
            test_passed = False
        
        # Test 3: Invalid guest directory
        print("\n3. Testing with invalid guest directory...")
        try:
            pyr0.build_guest("/nonexistent/path", "test")
            print("   ✗ Should have raised InvalidGuestDirectoryError!")
            test_passed = False
        except pyr0.InvalidGuestDirectoryError as e:
            print(f"   ✓ Correctly raised InvalidGuestDirectoryError: {str(e)[:60]}...")
        except Exception as e:
            print(f"   ✗ Wrong exception type: {type(e).__name__}: {e}")
            test_passed = False
        
        # Test 4: Directory without Cargo.toml
        print("\n4. Testing with directory lacking Cargo.toml...")
        temp_dir = Path("/tmp/test_no_cargo")
        temp_dir.mkdir(exist_ok=True)
        try:
            pyr0.build_guest(temp_dir, "test")
            print("   ✗ Should have raised InvalidGuestDirectoryError!")
            test_passed = False
        except pyr0.InvalidGuestDirectoryError as e:
            print(f"   ✓ Correctly raised InvalidGuestDirectoryError: {str(e)[:60]}...")
        except Exception as e:
            print(f"   ✗ Wrong exception type: {type(e).__name__}: {e}")
            test_passed = False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Test 5: Automatic binary name detection (positive test)
        print("\n5. Testing automatic binary name detection...")
        try:
            # Don't specify binary name, let it detect from Cargo.toml
            # This should now succeed because we correctly use the package name as-is
            start_time = time.time()
            elf_path = pyr0.build_guest(guest_dir)
            build_time = time.time() - start_time
            print(f"   ✓ Auto-detection succeeded: {elf_path.name}")
            print(f"   ⏱ Build time: {build_time:.2f} seconds")
            
            # Verify it found the correct binary
            if elf_path.name != "ed25519-guest-input":
                print(f"   ✗ Wrong binary name: expected 'ed25519-guest-input', got '{elf_path.name}'")
                test_passed = False
            else:
                print(f"   ✓ Correctly detected binary name from Cargo.toml")
        except Exception as e:
            print(f"   ✗ Auto-detection failed: {type(e).__name__}: {e}")
            test_passed = False
        
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
    """Run build_guest tests."""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 17 + "build_guest Test Suite" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    
    suite_start = time.time()
    test_passed = test_build_guest()
    suite_time = time.time() - suite_start
    
    print("\n" + "=" * 60)
    print(f"⏱ Total test suite time: {suite_time:.2f} seconds")
    if test_passed:
        print("✅ All build_guest tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())