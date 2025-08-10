# Create a new file called timestamp_utils.py

import time
from datetime import datetime
from typing import Union

def get_current_timestamp() -> float:
    """Get current time as float timestamp"""
    return time.time()

def convert_to_timestamp(time_value: Union[float, datetime, int]) -> float:
    """Convert various time formats to float timestamp"""
    if isinstance(time_value, float):
        return time_value
    elif isinstance(time_value, int):
        return float(time_value)
    elif isinstance(time_value, datetime):
        return time_value.timestamp()
    else:
        return time.time()  # Fallback to current time

def get_age_seconds(created_time: Union[float, datetime], current_time: float = None) -> float:
    """Calculate age in seconds from creation time"""
    if current_time is None:
        current_time = time.time()
    
    created_timestamp = convert_to_timestamp(created_time)
    return current_time - created_timestamp

# Alternative simplified trading loop section that's more robust:
def safe_order_age_check(order, current_time: float, max_age: float) -> bool:
    """Safely check if order is too old, handling any timestamp format"""
    try:
        if hasattr(order, 'created_at'):
            order_age = get_age_seconds(order.created_at, current_time)
        elif hasattr(order, 'created_datetime'):
            order_age = get_age_seconds(order.created_datetime, current_time)
        else:
            # No timestamp info, treat as old to be safe
            return True
        
        return order_age > max_age
    except Exception as e:
        print(f"   ⚠️ Error checking order age: {e}")
        return True  # Treat as old if we can't determine age