"""
Time Utility Functions

Unified time formatting utilities for the backend.
Eliminates duplicate strftime calls across the codebase.
"""
from datetime import datetime
from typing import Optional, Union


def format_timestamp(
    dt: Optional[datetime] = None,
    format_str: str = "%Y%m%d_%H%M%S"
) -> str:
    """
    Format datetime to string with unified format.
    
    Args:
        dt: Datetime object (defaults to now)
        format_str: strftime format string
        
    Returns:
        Formatted time string
        
    Examples:
        >>> format_timestamp()  # '20260515_204530'
        >>> format_timestamp(format_str="%Y-%m-%d %H:%M:%S")  # '2026-05-15 20:45:30'
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def get_timestamp_filename(prefix: str = "", suffix: str = "") -> str:
    """
    Generate filename with timestamp.
    
    Args:
        prefix: Filename prefix
        suffix: Filename suffix (without dot)
        
    Returns:
        Filename with timestamp
        
    Examples:
        >>> get_timestamp_filename("story", "json")  # 'story_20260515_204530.json'
        >>> get_timestamp_filename()  # '20260515_204530'
    """
    timestamp = format_timestamp()
    
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(timestamp)
    
    filename = "_".join(parts)
    if suffix:
        filename = f"{filename}.{suffix}"
    
    return filename


def format_datetime_full(dt: Optional[datetime] = None) -> str:
    """
    Format datetime to full readable format.
    
    Args:
        dt: Datetime object (defaults to now)
        
    Returns:
        Formatted datetime string
        
    Example:
        >>> format_datetime_full()  # '2026-05-15 20:45:30'
    """
    return format_timestamp(dt, format_str="%Y-%m-%d %H:%M:%S")


def format_date_only(dt: Optional[datetime] = None) -> str:
    """
    Format datetime to date only.
    
    Args:
        dt: Datetime object (defaults to now)
        
    Returns:
        Formatted date string
        
    Example:
        >>> format_date_only()  # '20260515'
    """
    return format_timestamp(dt, format_str="%Y%m%d")


def format_time_only(dt: Optional[datetime] = None) -> str:
    """
    Format datetime to time only.
    
    Args:
        dt: Datetime object (defaults to now)
        
    Returns:
        Formatted time string
        
    Example:
        >>> format_time_only()  # '204530'
    """
    return format_timestamp(dt, format_str="%H%M%S")
