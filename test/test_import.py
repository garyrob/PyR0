#!/usr/bin/env python3
"""Test what's actually available in pyr0."""

import pyr0
import pyr0._rust

print("In pyr0 module:")
for name in sorted(dir(pyr0)):
    if not name.startswith('_'):
        print(f"  {name}")

print("\nIn pyr0._rust module:")
for name in sorted(dir(pyr0._rust)):
    if not name.startswith('_'):
        obj = getattr(pyr0._rust, name)
        print(f"  {name}: {type(obj)}")

# Try to import v0.7.0 classes
print("\nv0.7.0 API imports:")
try:
    from pyr0._rust import Composer
    print("  ✓ Composer imported")
except ImportError as e:
    print(f"  ✗ Cannot import Composer: {e}")

try:
    from pyr0._rust import Claim
    print("  ✓ Claim imported")
except ImportError as e:
    print(f"  ✗ Cannot import Claim: {e}")

try:
    from pyr0._rust import ReceiptKind
    print("  ✓ ReceiptKind enum imported")
except ImportError as e:
    print(f"  ✗ Cannot import ReceiptKind: {e}")

try:
    from pyr0 import prove_succinct
    print("  ✓ prove_succinct function imported")
except ImportError as e:
    print(f"  ✗ Cannot import prove_succinct: {e}")

# Check custom exceptions
print("\nCustom exceptions:")
try:
    from pyr0 import CompositionError, VerificationError, PreflightError
    print("  ✓ Custom exceptions imported")
except ImportError as e:
    print(f"  ✗ Cannot import custom exceptions: {e}")