"""PATHOS being core."""
import sys

# PCAN on darwin patch
try:
    import can
    import canopen
    if sys.platform.startswith('darwin'):
        from being.can.pcan_darwin_patch import patch_pcan_on_darwin
        patch_pcan_on_darwin()
except ImportError:
    pass

__author__ = 'atheler'
__version__ = '0.3.6'
