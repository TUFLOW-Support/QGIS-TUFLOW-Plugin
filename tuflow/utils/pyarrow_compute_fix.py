import pandas as pd

# Try importing pyarrow and checking for the function
try:
    import pyarrow.compute as pc
    if not hasattr(pc, "match_substring_regex"):
        # Switch to Python string backend globally
        pd.set_option("mode.string_storage", "python")
except ImportError:
    # No PyArrow installed — fallback to Python backend
    pd.set_option("mode.string_storage", "python")
