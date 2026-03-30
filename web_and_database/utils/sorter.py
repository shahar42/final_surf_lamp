import ctypes
import os
from typing import List, Tuple

class IndexedValue(ctypes.Structure):
    _fields_ = [("value", ctypes.c_float),
                ("index", ctypes.c_int)]

# Load the library
lib_path = os.path.join(os.path.dirname(__file__), '../../surf-lamp-processor/merge_sort/libmergesort.so')
try:
    lib = ctypes.CDLL(lib_path)
    # Define the function signature
    lib.merge_sort_array_indexed.argtypes = [ctypes.POINTER(IndexedValue), ctypes.c_int]
    lib.merge_sort_array_indexed.restype = None
    HAS_LIBSORT = True
except Exception as e:
    print(f"Warning: Could not load libmergesort.so: {e}")
    HAS_LIBSORT = False

def sort_by_wave_height(data: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """
    Sorts a list of (location_name, wave_height) tuples using the C merge sort.
    Returns the sorted list in descending order (highest wave first).
    """
    if not HAS_LIBSORT or not data:
        # Fallback to Python sort if C lib is missing
        return sorted(data, key=lambda x: x[1], reverse=True)

    n = len(data)
    # Create the array of structures
    arr = (IndexedValue * n)()
    for i, (name, val) in enumerate(data):
        arr[i].value = float(val) if val is not None else 0.0
        arr[i].index = i

    # Call the C function
    lib.merge_sort_array_indexed(arr, n)

    # Reconstruct the list using the sorted indices, in reverse (descending)
    sorted_data = []
    for i in range(n - 1, -1, -1):
        original_idx = arr[i].index
        sorted_data.append(data[original_idx])

    return sorted_data
