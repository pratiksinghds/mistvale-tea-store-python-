"""Drives the real Streamlit app (no browser) through the shopping flow."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def start() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def sidebar_text(at: AppTest) -> str:
    parts = [m.value for m in at.sidebar.markdown] + [h.value for h in at.sidebar.header]
    return " | ".join(str(p) for p in parts)


def test_page_renders_all_sections():
    at = start()
    headers = [h.value for h in at.main.header]
    assert headers == ["Our teas", "Check delivery to your pincode", "What tea drinkers say",
                       "Questions, answered", "Stay in touch"]
    assert len(at.expander) == 6                       # FAQ
    assert at.title[0].value == "Hill-grown tea, honestly made."


def test_add_change_qty_coupon_flow():
    at = start()
    at.button(key="add_104").click().run()             # Masala Chai, ₹399
    assert at.session_state.cart == {104: 1}
    at.number_input(key="qty_104").set_value(3).run()
    assert at.session_state.cart == {104: 3}
    at.text_input(key="coupon_input").input("welcome10").run()
    at.button(key="coupon_apply").click().run()
    assert at.session_state.coupon == "WELCOME10"
    text = sidebar_text(at)
    assert "₹1,077" in text                            # 1197 - 119.70, free shipping


def test_sold_out_button_disabled():
    at = start()
    assert at.button(key="add_107").disabled


def test_limit_of_five_on_card():
    at = start()
    for _ in range(6):
        btn = at.button(key="add_102")
        if btn.disabled:
            break
        btn.click().run()
    assert at.session_state.cart == {102: 5}
    assert at.button(key="add_102").disabled


def test_filters_and_search_together():
    at = start()
    at.text_input(key="query").input("tea").run()
    at.session_state.category = "Green"
    at.selectbox(key="sort").set_value("Highest price").run()
    names = [m.value for m in at.markdown if str(m.value).startswith("#### ")]
    assert names == ["#### Kashmiri Kahwa", "#### Nilgiri Green Tea"]


def test_pincode_invalid_shows_error():
    at = start()
    at.text_input(key="pin").input("012345")
    at.button(key="pin_check").click().run()
    assert any("not a valid pincode" in e.value for e in at.error)
