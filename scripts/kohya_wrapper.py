#!/usr/bin/env python
"""
Kohya wrapper script for macOS sandbox compatibility.
Patches multiprocessing.Value before executing Kohya training script.
"""
import sys
import os

# Patch multiprocessing.Value BEFORE importing anything from Kohya
import multiprocessing

class SimpleValue:
    """Simple alternative to multiprocessing.Value for single-threaded use"""
    __slots__ = ['_value']
    
    def __init__(self, typecode, value):
        self._value = value
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val

# Save original
_original_Value = multiprocessing.Value

def _patched_Value(typecode_or_type, *args, **kwargs):
    """Try multiprocessing.Value, fallback to SimpleValue on macOS sandbox"""
    try:
        return _original_Value(typecode_or_type, *args, **kwargs)
    except (PermissionError, OSError):
        # Determine initial value based on typecode
        if isinstance(typecode_or_type, str):
            initial = 0 if typecode_or_type in ('i', 'l', 'q') else 0.0
        else:
            initial = 0
        return SimpleValue(initial)

# Apply patch
multiprocessing.Value = _patched_Value
multiprocessing.RawValue = _patched_Value

# Add Kohya's sd-scripts directory to Python path
# This script is called as: python kohya_wrapper.py <kohya_script> [args...]
if len(sys.argv) < 2:
    print("Usage: python kohya_wrapper.py <kohya_script.py> [args...]")
    sys.exit(1)

kohya_script = sys.argv[1]
kohya_args = sys.argv[2:]

# Add Kohya script directory to sys.path
kohya_script_dir = os.path.dirname(os.path.abspath(kohya_script))
if kohya_script_dir not in sys.path:
    sys.path.insert(0, kohya_script_dir)

# Update sys.argv for Kohya script
sys.argv = [kohya_script] + kohya_args

# Execute Kohya script
exec(open(kohya_script).read())
