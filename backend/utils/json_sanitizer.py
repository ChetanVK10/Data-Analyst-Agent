import math
import pandas as pd
import numpy as np
import datetime

def sanitize_for_json(obj):
    """
    Recursively sanitizes an object to ensure it is fully JSON serializable.
    Converts:
    - float NaN, Infinity, -Infinity to None
    - pd.NA, pd.NaT to None
    - numpy scalars (int, float, bool) to native Python types
    - datetime objects to ISO strings
    """
    if obj is None:
        return None
        
    # Handle pandas NA types explicitly
    if obj is pd.NA or obj is pd.NaT or type(obj).__name__ in ('NAType', 'NaTType'):
        return None
        
    if isinstance(obj, dict):
        # Handle Plotly's typed-array/binary encoding (bdata)
        if "bdata" in obj and "dtype" in obj:
            try:
                import base64
                bdata = base64.b64decode(obj["bdata"])
                # Plotly's dtype strings map directly to numpy dtypes (e.g., 'i2', 'f8', 'float64')
                arr = np.frombuffer(bdata, dtype=obj["dtype"])
                if "shape" in obj and isinstance(obj["shape"], str):
                    # Plotly shapes are like "5,1" which we can safely ignore and just flatten to 1D
                    pass
                return sanitize_for_json(arr.tolist())
            except Exception:
                pass
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
        
    if isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
        
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
        
    if isinstance(obj, tuple):
        return [sanitize_for_json(v) for v in obj] # JSON uses lists
        
    if isinstance(obj, float) or isinstance(obj, np.floating):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
        
    if isinstance(obj, np.integer):
        return int(obj)
        
    if isinstance(obj, np.bool_):
        return bool(obj)
        
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
        
    return obj
