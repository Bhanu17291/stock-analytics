# utils/helpers.py
"""
Shared utilities: retry logic, formatting helpers, and safe accessors.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator that retries a function on failure.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        delay:        Seconds to wait between retries (doubles each attempt).
        exceptions:   Exception types that trigger a retry.

    Example:
        @retry(max_attempts=3, delay=1.0)
        def flaky_network_call():
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    wait = delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, e, wait,
                    )
                    if attempt < max_attempts:
                        time.sleep(wait)
            logger.error("%s failed after %d attempts", func.__name__, max_attempts)
            raise last_exc
        return wrapper  # type: ignore
    return decorator


def fmt_market_cap(val: float) -> str:
    """Format a market cap number into a human-readable string."""
    if not val:
        return "N/A"
    if val >= 1e12:
        return f"${val / 1e12:.2f}T"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    if val >= 1e6:
        return f"${val / 1e6:.2f}M"
    return f"${val:,.0f}"


def currency_symbol(currency: str) -> str:
    """Return the currency symbol for a given currency code."""
    return {"INR": "₹", "GBP": "£", "EUR": "€", "JPY": "¥"}.get(currency.upper(), "$")


def safe_round(val: Any, decimals: int = 2) -> float:
    """Safely round a value to N decimals, returning 0.0 on failure."""
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return 0.0