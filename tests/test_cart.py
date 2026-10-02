from decimal import Decimal

import pytest

from mistvale import api
from mistvale.cart import (add, browse, checkout_payload, clean_cart, inr, remove, set_qty,
                           totals, validate_coupon)


# R1 / R5: prices from data, Indian grouping, only the total rounded
def test_inr_formatting():
    assert inr(1299) == "₹1,299"
    assert inr(123456) == "₹1,23,456"
    assert inr(Decimal("34.9")) == "₹34.90"
    assert inr(-150) == "−₹150"


def test_masala_with_coupon_rounds_only_total():
    t = totals({104: 1}, "welcome10")
    assert t.discount == Decimal("39.9")
    assert t.shipping == 49            # 359.10 after discount < 599
    assert t.total == 408              # round(359.10 + 49)


# R2: max 5, never above stock
def test_limit_of_five():
    cart = {}
    for _ in range(8):
        cart, _, _ = add(cart, 102)
    assert cart == {102: 5}


def test_stock_below_five():
    cart, added, msg = add({}, 108, 20)    # sampler stock is 9 -> capped at 5
    assert cart == {108: 5} and added == 5 and "up to 5" in msg


def test_set_qty_clamps():
    assert set_qty({101: 1}, 101, 9) == {101: 5}
    assert set_qty({101: 3}, 101, 0) == {101: 1}


def test_remove_only_that_line():
    assert remove({101: 1, 102: 2, 103: 1}, 102) == {101: 1, 103: 1}


# R3: coupon
def test_coupon_needs_399_subtotal():
    ok, msg = validate_coupon({101: 1}, "WELCOME10")
    assert not ok and "₹50" in msg


def test_coupon_excludes_gifts():
    ok, _ = validate_coupon({108: 1}, "welcome10")
    assert not ok
    t = totals({108: 1, 101: 1}, "WELCOME10")
    assert t.discount == Decimal("34.9")          # 10% of the Assam only


def test_coupon_cap_150():
    assert totals({102: 5}, " Welcome10 ").discount == 150


def test_unknown_code():
    assert validate_coupon({102: 1}, "SAVE50") == (False, "That is not a valid code.")


# R4: free shipping counted after the discount
def test_free_shipping_after_discount():
    t = totals({101: 2}, "WELCOME10")             # 698 - 69.80 = 628.20 -> free
    assert t.shipping == 0 and t.total == 628
    assert totals({101: 1}).shipping == 49
    assert totals({}).shipping == 0


# R6: sold out
def test_sold_out_cannot_be_added():
    cart, added, _ = add({}, 107)
    assert cart == {} and added == 0


@pytest.mark.parametrize("sort", ["Featured", "Lowest price", "Highest price", "Name A–Z"])
def test_sold_out_sorts_last(sort):
    assert browse(sort=sort)[-1].id == 107


# R7: filter + search + sort together
def test_filter_search_sort_together():
    ids = api.search("tea")
    result = browse(category="Green", sort="Highest price", query="tea", match_ids=ids)
    assert [p.id for p in result] == [103, 105]


def test_category_is_case_insensitive():
    assert [p.id for p in browse(category="green")] == [103, 105]


# R8: delivery check
def test_pincodes():
    assert api.check_pincode("734001", simulate_latency=False) == {"serviceable": True, "days": 2}
    assert api.check_pincode("999999", simulate_latency=False) == {"serviceable": False}
    for bad in ["012345", "7340", "", "abcdef"]:
        with pytest.raises(api.InvalidPincode):
            api.check_pincode(bad, simulate_latency=False)


# Saved cart and checkout contract
def test_clean_cart_drops_bad_entries():
    assert clean_cart({"102": "21", 107: 2, 999: 1, 104: "x"}) == {102: 5}


def test_checkout_payload():
    assert checkout_payload({104: 2, 108: 1}, "welcome10") == {
        "items": [{"id": 104, "qty": 2}, {"id": 108, "qty": 1}], "coupon": "WELCOME10"}
    assert checkout_payload({101: 1}, "WELCOME10")["coupon"] == ""   # below Rs 399: not sent
