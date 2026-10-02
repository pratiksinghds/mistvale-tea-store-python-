"""Cart rules (R1-R6). Pure functions over a cart of {product_id: qty}; no UI code here.

R1  Prices always come from PRODUCTS, per pack, GST included.
R2  At most 5 of a product, and never more than its stock.
R3  WELCOME10: 10% off eligible items (not Gifts), capped at Rs 150, subtotal >= Rs 399,
    case-insensitive, one coupon per order, applying twice changes nothing.
R4  Shipping Rs 49, free when the amount after the discount reaches Rs 599.
R5  Only the final total is rounded; amounts shown with Rs and Indian digit grouping.
R6  Sold-out products can't be added and sort last in every order.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .data import BY_ID, PRODUCTS, Product

MAX_PER_PRODUCT = 5
SHIPPING_FEE = 49
FREE_SHIPPING_FROM = 599
COUPON_CODE = "WELCOME10"
COUPON_PERCENT = 10
COUPON_CAP = 150
COUPON_MIN_SUBTOTAL = 399
COUPON_EXCLUDED = {"Gifts"}

Cart = dict[int, int]


def max_qty(p: Product) -> int:
    return max(0, min(MAX_PER_PRODUCT, p.stock))


def clean_cart(raw) -> Cart:
    """Drop unknown or sold-out ids and bad quantities; cap at the limit."""
    out: Cart = {}
    if not isinstance(raw, dict):
        return out
    for key, qty in raw.items():
        try:
            pid, q = int(key), int(qty)
        except (TypeError, ValueError):
            continue
        p = BY_ID.get(pid)
        if p and not p.sold_out and q > 0:
            out[pid] = min(max_qty(p), out.get(pid, 0) + q)
    return out


def add(cart: Cart, pid: int, qty: int = 1) -> tuple[Cart, int, str]:
    """Return (new cart, how many were added, message)."""
    p = BY_ID.get(pid)
    if p is None:
        return cart, 0, "Unknown product."
    if p.sold_out:
        return cart, 0, f"{p.name} is sold out."
    current = cart.get(pid, 0)
    room = max_qty(p) - current
    added = max(0, min(qty, room))
    if added == 0:
        return cart, 0, limit_message(p)
    new = dict(cart)
    new[pid] = current + added
    if added < qty:
        return new, added, f"Added {added}. {limit_message(p)}"
    return new, added, f"Added {added} × {p.name}" if added > 1 else f"Added {p.name}"


def set_qty(cart: Cart, pid: int, qty: int) -> Cart:
    p = BY_ID.get(pid)
    if p is None or pid not in cart:
        return cart
    new = dict(cart)
    new[pid] = max(1, min(max_qty(p), int(qty)))
    return new


def remove(cart: Cart, pid: int) -> Cart:
    return {k: v for k, v in cart.items() if k != pid}


def limit_message(p: Product) -> str:
    if p.stock < MAX_PER_PRODUCT:
        return f"Only {p.stock} of {p.name} left, and they are all in your cart."
    return f"You can buy up to {MAX_PER_PRODUCT} of each tea."


def item_count(cart: Cart) -> int:
    return sum(cart.values())


def normalise_code(code: str) -> str:
    return str(code).strip().upper()


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    eligible: Decimal
    discount: Decimal
    after_discount: Decimal
    shipping: Decimal
    total: int
    coupon_note: str


def totals(cart: Cart, coupon: str = "") -> Totals:
    """All maths in Decimal; only the final total is rounded (R5)."""
    subtotal = eligible = Decimal(0)
    for pid, qty in cart.items():
        p = BY_ID[pid]
        line = Decimal(p.price) * qty
        subtotal += line
        if p.category not in COUPON_EXCLUDED:
            eligible += line

    discount, note = Decimal(0), ""
    if normalise_code(coupon) == COUPON_CODE:
        if subtotal < COUPON_MIN_SUBTOTAL:
            note = f"Add {inr(COUPON_MIN_SUBTOTAL - subtotal)} more to use {COUPON_CODE} (orders from {inr(COUPON_MIN_SUBTOTAL)})."
        elif eligible == 0:
            note = f"{COUPON_CODE} does not apply to gift boxes. Add a tea to use it."
        else:
            discount = min(eligible * COUPON_PERCENT / 100, Decimal(COUPON_CAP))

    after = subtotal - discount
    shipping = Decimal(0) if not cart or after >= FREE_SHIPPING_FROM else Decimal(SHIPPING_FEE)
    total = int((after + shipping).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return Totals(subtotal, eligible, discount, after, shipping, total, note)


def validate_coupon(cart: Cart, code: str) -> tuple[bool, str]:
    """Whether a typed code can be applied right now, and the message to show."""
    code = normalise_code(code)
    if not code:
        return False, "Enter a coupon code."
    if code != COUPON_CODE:
        return False, "That is not a valid code."
    t = totals(cart)
    if t.subtotal < COUPON_MIN_SUBTOTAL:
        return False, (f"{COUPON_CODE} works on orders from {inr(COUPON_MIN_SUBTOTAL)}. "
                       f"Add {inr(COUPON_MIN_SUBTOTAL - t.subtotal)} more to use it.")
    if t.eligible == 0:
        return False, f"{COUPON_CODE} does not apply to gift boxes."
    saved = totals(cart, code).discount
    capped = " (maximum)" if saved >= COUPON_CAP else ""
    return True, f"You saved {inr(saved)}{capped}."


def checkout_payload(cart: Cart, coupon: str) -> dict:
    """The checkout contract: items as [{"id", "qty"}] and the coupon only while it gives a discount."""
    cart = clean_cart(cart)
    t = totals(cart, coupon)
    return {
        "items": [{"id": pid, "qty": qty} for pid, qty in cart.items()],
        "coupon": COUPON_CODE if t.discount > 0 else "",
    }


def inr(amount) -> str:
    """Rs with Indian digit grouping, e.g. 123456 -> '₹1,23,456', 34.9 -> '₹34.90'."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = value < 0
    value = abs(value)
    rupees, paise = divmod(value, 1)
    digits = str(int(rupees))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    text = "₹" + digits + (f".{int(paise * 100):02d}" if paise else "")
    return "−" + text if negative else text


SORTS = {
    "Featured": None,
    "Lowest price": lambda p: (p.price, p.name),
    "Highest price": lambda p: (-p.price, p.name),
    "Name A–Z": lambda p: p.name.lower(),
}
FEATURED_ORDER = {p.id: i for i, p in enumerate(PRODUCTS)}


def browse(category: str = "All", sort: str = "Featured", query: str = "",
           saved: set[int] | None = None, match_ids: list[int] | None = None) -> list[Product]:
    """Filter + search + sort together (R7); sold-out always last (R6)."""
    items = []
    for p in PRODUCTS:
        if category == "Saved":
            if not saved or p.id not in saved:
                continue
        elif category != "All" and p.category.lower() != category.lower():
            continue
        if query.strip() and match_ids is not None and p.id not in match_ids:
            continue
        items.append(p)
    key = SORTS.get(sort) or (lambda p: FEATURED_ORDER[p.id])
    return sorted(items, key=lambda p: (p.sold_out, key(p)))
