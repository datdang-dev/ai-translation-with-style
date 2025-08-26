"""
Data models for the translation service
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class BatchJob:
    """Represents a single translation job"""
    input_path: str
    output_path: str
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    # Use monotonic clock for reliable duration calculations
    start_monotonic: Optional[float] = None
    end_monotonic: Optional[float] = None