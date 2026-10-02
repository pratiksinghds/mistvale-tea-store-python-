"""Simulated store backend (search and delivery estimate), ported from the original JS API."""
import random
import re
import time

from .data import PRODUCTS

DELIVERY_ZONES = {"73": 2, "70": 3, "71": 3, "11": 4, "40": 4, "56": 5, "60": 5, "50": 5}
PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")


class InvalidPincode(ValueError):
    """Raised for anything that is not a valid 6-digit Indian pincode."""


def search(query: str) -> list[int]:
    """Ids of products whose name or description contains the query (case-insensitive)."""
    q = str(query).strip().lower()
    return [p.id for p in PRODUCTS if q in p.name.lower() or q in p.desc.lower()]


def check_pincode(pin: str, simulate_latency: bool = True) -> dict:
    """Delivery estimate for a pincode: {"serviceable": True, "days": n} or {"serviceable": False}."""
    if simulate_latency:
        time.sleep(0.4 + random.random() * 0.6)
    pin = str(pin).strip()
    if not PINCODE_RE.match(pin):
        raise InvalidPincode(pin)
    days = DELIVERY_ZONES.get(pin[:2])
    return {"serviceable": True, "days": days} if days else {"serviceable": False}
