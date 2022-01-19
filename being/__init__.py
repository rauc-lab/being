"""PATHOS being core."""
import sys


# python-can PCAN on darwin patch. This is issue will get fixed with python-can
# >= 4.0.0
try:
    import can
    import canopen
    from being.can.pcan_darwin_patch import (
        is_pcan_lib_installed,
        does_python_can_need_patching,
        patch_pcan_on_darwin,
    )

    if (sys.platform.startswith('darwin')
        and is_pcan_lib_installed()
        and does_python_can_need_patching()
    ):
        patch_pcan_on_darwin()
except ImportError:
    pass



__author__ = 'atheler'
__version__ = '1.0.2'
