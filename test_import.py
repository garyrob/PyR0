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

# Try to import ExecutorEnv directly
try:
    from pyr0._rust import ExecutorEnv
    print("\nExecutorEnv imported directly from _rust!")
except ImportError as e:
    print(f"\nCannot import ExecutorEnv from _rust: {e}")

# Try to get prove_with_env
try:
    from pyr0._rust import prove_with_env
    print("prove_with_env imported directly from _rust!")
except ImportError as e:
    print(f"Cannot import prove_with_env from _rust: {e}")