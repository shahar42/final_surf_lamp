import os
import ctypes
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Constants to match C implementation
IMPOSSIBLE_THRESHOLD = 9999.0

# Path handling for the shared library
_current_dir = os.path.dirname(os.path.abspath(__file__))
_lib_path = os.path.join(_current_dir, "libthreshold.so")

# Internal reference to the loaded library
_lib = None

try:
    if os.path.exists(_lib_path):
        _lib = ctypes.CDLL(_lib_path)
        # Define argument and return types
        # C signature: float ThreshCalculator(float curr_value, float user_min, float user_max)
        _lib.ThreshCalculator.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
        _lib.ThreshCalculator.restype = ctypes.c_float
    else:
        logger.warning(f"Shared library not found at {_lib_path}. Using Python fallback.")
except Exception as e:
    logger.error(f"Error loading shared library: {e}. Using Python fallback.")
    _lib = None

def _calculate_effective_threshold_python(current_value, user_min, user_max):
    """Pure Python implementation as fallback."""
    # Handle None values (convert to -1.0 sentinel)
    curr = -1.0 if current_value is None else float(current_value)
    u_min = -1.0 if user_min is None else float(user_min)
    u_max = -1.0 if user_max is None else float(user_max)

    if curr == -1.0 or u_max == -1.0:
        return u_min
    
    if curr > u_max:
        return IMPOSSIBLE_THRESHOLD
        
    return u_min

def calculate_effective_threshold(current_value, user_min, user_max):
    """
    Python wrapper that uses C acceleration if available.
    Converts None values to -1.0 for C compatibility.
    """
    if _lib is not None:
        try:
            # Prepare values for C (convert None to -1.0)
            curr = -1.0 if current_value is None else float(current_value)
            u_min = -1.0 if user_min is None else float(user_min)
            u_max = -1.0 if user_max is None else float(user_max)
            
            return float(_lib.ThreshCalculator(curr, u_min, u_max))
        except Exception as e:
            logger.error(f"C calculation failed: {e}. Falling back to Python.")
            return _calculate_effective_threshold_python(current_value, user_min, user_max)
    else:
        return _calculate_effective_threshold_python(current_value, user_min, user_max)