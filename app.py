"""Mistvale Tea Co. - online tea store, built in Python with Streamlit.

Run:  streamlit run app.py
"""
import re
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st

from mistvale import api
from mistvale import cart as rules
from mistvale.data import BY_ID, CATEGORY_LABEL, COMPANY, COPYRIGHT, FAQ, IMAGES, LEGAL, PRODUCTS, REVIEWS

CHECKOUT_URL = "https://mistvale.example/cart/checkout"
CATEGORIES = ["All", "Black", "Green", "Herbal", "Gifts", "Saved"]
SORT_OPTIONS = list(rules.SORTS)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")

st.set_page_config(
    page_title="Mistvale Tea Co. | Hill-grown Indian tea, honestly made",
    page_icon=str(IMAGES / "logo-mark.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- state
ss = st.session_state
ss.setdefault("cart", {})            # {product_id: qty}
ss.setdefault("coupon", "")          # applied coupon code
ss.setdefault("coupon_msg", ("", ""))  # (kind, text)
ss.setdefault("wishlist", set())
ss.setdefault("recent", [])
ss.setdefault("flash", None)         # toast shown on the next run
ss.setdefault("nl_email", "")

# Filters start from the URL so links can be shared (?cat=green&sort=Lowest+price&q=chai)
if "filters_loaded" not in ss:
    qp = st.query_params
    cat = qp.get("cat", "All").capitalize()
    ss.category = cat if cat in CATEGORIES and cat != "Saved" else "All"
    ss.sort = qp.get("sort") if qp.get("sort") in SORT_OPTIONS else "Featured"
    ss.query = qp.get("q", "")
    ss.filters_loaded = True


def sync_url():
    params = {}
    if ss.get("category") not in (None, "All", "Saved"):
        params["cat"] = ss.category.lower()
    if ss.get("sort", "Featured") != "Featured":
        params["sort"] = ss.sort
    if ss.get("query", "").strip():
        params["q"] = ss.query.strip()
    st.query_params.from_dict(params)


# ---------------------------------------------------------------- actions (widget callbacks)
def add_to_cart(pid: int, qty: int = 1):
    ss.cart, added, msg = rules.add(ss.cart, pid, qty)
    ss.flash = (msg, ":material/check_circle:" if added else ":material/info:")


def change_qty(pid: int):
    ss.cart = rules.set_qty(ss.cart, pid, ss[f"qty_{pid}"])


def remove_line(pid: int):
    ss.cart = rules.remove(ss.cart, pid)
    ss.flash = (f"Removed {BY_ID[pid].name}.", ":material/delete:")


def toggle_wish(pid: int):
    if pid in ss.wishlist:
        ss.wishlist.discard(pid)
        ss.flash = ("Removed from saved teas.", ":material/heart_minus:")
    else:
        ss.wishlist.add(pid)
        ss.flash = (f"Saved {BY_ID[pid].name} for later.", ":material/favorite:")


def apply_coupon():
    ok, msg = rules.validate_coupon(ss.cart, ss.coupon_input)
    if ok:
        ss.coupon = rules.COUPON_CODE
        ss.coupon_input = ""
    ss.coupon_msg = ("success" if ok else "error", msg)


def remove_coupon():
    ss.coupon = ""
    ss.coupon_msg = ("info", "Coupon removed.")


def remember(pid: int):
    ss.recent = [pid] + [x for x in ss.recent if x != pid][:3]


# ---------------------------------------------------------------- dialogs
@st.dialog("Tea details", width="large")
def quick_view(pid: int):
    p = BY_ID[pid]
    remember(pid)
    left, right = st.columns([1, 1], gap="large")
    left.image(p.image_path, caption=None, width="stretch")
    with right:
        st.caption(CATEGORY_LABEL[p.category])
        st.subheader(p.name)
        if p.rating:
            st.markdown(f":material/star: **{p.rating}** out of 5 · {p.reviews:,} reviews")
        st.write(p.desc)
        st.markdown(f"### {rules.inr(p.price)}")
        st.caption("per pack, incl. GST")
        in_cart = ss.cart.get(pid, 0)
        room = rules.max_qty(p) - in_cart
        if p.sold_out:
            st.button("Sold out", disabled=True, width="stretch")
        elif room <= 0:
            st.info(f"{in_cart} in your cart, the most you can buy.", icon=":material/shopping_bag:")
        else:
            qty = st.number_input("Quantity", min_value=1, max_value=room, value=1, step=1)
            if st.button(f"Add to cart · {rules.inr(p.price * qty)}", type="primary", width="stretch"):
                add_to_cart(pid, int(qty))
                st.rerun()
        note = "Sold out right now." if p.sold_out else f"Up to {rules.max_qty(p)} per order."
        if p.stock and p.stock <= 10:
            note = f"Only {p.stock} left. " + note
        if in_cart:
            note += f" {in_cart} already in your cart."
        st.caption(note)

    also = [x for x in PRODUCTS if x.id != pid and not x.sold_out]
    also.sort(key=lambda x: (x.category != p.category, rules.FEATURED_ORDER[x.id]))
    st.markdown("##### You may also like")
    for col, x in zip(st.columns(3), also[:3]):
        with col:
            st.image(x.image_path, width="stretch")
            st.markdown(f"**{x.name}**  \n{rules.inr(x.price)}")


@st.dialog("Checkout")
def checkout_dialog():
    payload = rules.checkout_payload(ss.cart, ss.coupon)
    t = rules.totals(ss.cart, ss.coupon)
    st.write(f"**{rules.item_count(ss.cart)} items · total {rules.inr(t.total)}** (incl. GST)")
    st.caption("This is the data sent to the store's checkout API:")
    st.json(payload)
    try:
        body = urllib.parse.urlencode({"items": str(payload["items"]).replace("'", '"'),
                                       "coupon": payload["coupon"]}).encode()
        urllib.request.urlopen(urllib.request.Request(CHECKOUT_URL, data=body, method="POST"), timeout=5)
        st.success("Order sent. You'll be taken to payment next.")
    except (urllib.error.URLError, OSError):
        st.warning("This demo's checkout address is a placeholder, so the order was not placed. "
                   "Payment and delivery details would be collected on the next step.",
                   icon=":material/info:")


# ---------------------------------------------------------------- flash message from the last action
if ss.flash:
    st.toast(ss.flash[0], icon=ss.flash[1])
    ss.flash = None

# ---------------------------------------------------------------- sidebar: cart
with st.sidebar:
    count = rules.item_count(ss.cart)
    st.header(f"Your cart · {count} item{'s' if count != 1 else ''}")
    if not ss.cart:
        st.write("Your cart is empty. Find a tea you'll love and it will appear here.")
    else:
        t = rules.totals(ss.cart, ss.coupon)
        remaining = rules.FREE_SHIPPING_FROM - t.after_discount
        if remaining <= 0:
            st.success("You have free shipping.", icon=":material/local_shipping:")
        else:
            st.progress(min(1.0, float(t.after_discount) / rules.FREE_SHIPPING_FROM),
                        text=f"Add {rules.inr(remaining)} more for free shipping")

        for pid, qty in list(ss.cart.items()):
            p = BY_ID[pid]
            with st.container(border=True):
                img, info = st.columns([1, 2.2])
                img.image(p.image_path, width="stretch")
                info.markdown(f"**{p.name}**  \n{rules.inr(p.price)} per pack")
                if p.category in rules.COUPON_EXCLUDED:
                    info.caption("Not eligible for coupons")
                ss[f"qty_{pid}"] = qty
                q, total, rm = st.columns([1.3, 1, 0.6], vertical_alignment="bottom")
                q.number_input("Quantity", min_value=1, max_value=rules.max_qty(p), step=1,
                               key=f"qty_{pid}", on_change=change_qty, args=(pid,))
                total.markdown(f"**{rules.inr(p.price * qty)}**")
                rm.button(":material/delete:", key=f"rm_{pid}", help=f"Remove {p.name}",
                          on_click=remove_line, args=(pid,))
                if qty >= rules.max_qty(p):
                    st.caption(f"Only {p.stock} in stock" if p.stock < rules.MAX_PER_PRODUCT
                               else f"Limit of {rules.MAX_PER_PRODUCT} per tea")

        # coupon
        if ss.coupon:
            st.success(f"{ss.coupon} applied" if t.discount else f"{ss.coupon} added, not active yet",
                       icon=":material/sell:")
            if t.coupon_note:
                st.caption(t.coupon_note)
            st.button("Remove coupon", on_click=remove_coupon)
        else:
            with st.form("coupon_form", border=False, clear_on_submit=False):
                c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
                c1.text_input("Coupon code", key="coupon_input")
                c2.form_submit_button("Apply", on_click=apply_coupon, width="stretch", key="coupon_apply")
            st.caption(f"New here? Try **{rules.COUPON_CODE}** for 10% off teas on orders from "
                       f"{rules.inr(rules.COUPON_MIN_SUBTOTAL)}.")
        kind, msg = ss.coupon_msg
        if msg:
            {"success": st.success, "error": st.error, "info": st.info}[kind](msg)
            ss.coupon_msg = ("", "")

        # totals
        t = rules.totals(ss.cart, ss.coupon)
        rows = [("Subtotal", rules.inr(t.subtotal))]
        if t.discount:
            rows.append((f"Discount ({ss.coupon})", "−" + rules.inr(t.discount)))
        rows.append(("Shipping", rules.inr(t.shipping) if t.shipping else "Free"))
        for label, value in rows:
            a, b = st.columns([2, 1])
            a.write(label)
            b.write(value)
        st.divider()
        a, b = st.columns([2, 1])
        a.markdown("**Total** (incl. GST)")
        b.markdown(f"**{rules.inr(t.total)}**")
        if st.button("Checkout", type="primary", width="stretch"):
            checkout_dialog()

# ---------------------------------------------------------------- header + hero
st.caption("Free shipping on orders from ₹599 · All prices include GST")
brand, nav = st.columns([1, 2], vertical_alignment="center")
brand.image(str(IMAGES / "logo.svg"), width=220)
nav.markdown("[Shop](#our-teas) · [Delivery](#check-delivery-to-your-pincode) · "
             "[Reviews](#what-tea-drinkers-say) · [FAQ](#questions-answered)")

hero_text, hero_img = st.columns([1.05, 1], gap="large", vertical_alignment="center")
with hero_text:
    st.caption(f"Since {COMPANY['founded']} · Siliguri, West Bengal")
    st.title(COMPANY["tagline"], anchor=False)
    st.write("Malty Assam for your morning cup, a delicate, floral Darjeeling first flush, bold masala chai "
             "and a caffeine-free chamomile and tulsi blend. We deliver within India in 2 to 5 working days.")
    st.markdown("**[Shop the teas →](#our-teas)**")
with hero_img:
    st.image(str(IMAGES / "hero-banner.webp"), width="stretch")

trust = st.columns(4)
for col, (icon, text) in zip(trust, [
    ("receipt_long", "All prices include GST"),
    ("local_shipping", "Free shipping from ₹599"),
    ("schedule", "Delivery in 2 to 5 working days"),
    ("undo", "7-day returns on unopened packs"),
]):
    col.markdown(f":material/{icon}: **{text}**")
st.divider()

# ---------------------------------------------------------------- shop
st.header("Our teas")
st.write("Every price is per pack and includes GST.")
f1, f2, f3 = st.columns([1.2, 2, 1], vertical_alignment="bottom")
f1.text_input("Search teas", key="query", on_change=sync_url, placeholder="e.g. chai, green, floral")
f2.pills("Category", CATEGORIES, key="category", on_change=sync_url,
         format_func=lambda c: f"Saved ({len(ss.wishlist)})" if c == "Saved" else c)
f3.selectbox("Sort by", SORT_OPTIONS, key="sort", on_change=sync_url)

category = ss.category or "All"
query = ss.query.strip()
items = rules.browse(category=category, sort=ss.sort, query=query, saved=ss.wishlist,
                     match_ids=api.search(query) if query else None)

st.caption(f"{len(items)} tea{'s' if len(items) != 1 else ''}" + (f" for “{query}”" if query else ""))
if not items:
    if category == "Saved" and not query:
        st.info("You have not saved any teas yet. Tap the heart on a tea to keep it here.")
    else:
        st.info("No teas match. Try another word or category.")

PER_ROW = 4
for start in range(0, len(items), PER_ROW):
    for col, p in zip(st.columns(PER_ROW), items[start:start + PER_ROW]):
        with col, st.container(border=True, height="stretch"):
            st.image(p.image_path, width="stretch")
            if p.sold_out:
                st.badge("Sold out", color="gray")
            elif p.stock <= 10:
                st.badge(f"Only {p.stock} left", color="orange")
            st.caption(CATEGORY_LABEL[p.category])
            st.markdown(f"#### {p.name}")
            if p.rating:
                st.markdown(f":material/star: **{p.rating}** ({p.reviews:,} reviews)")
            st.write(p.desc)
            st.markdown(f"**{rules.inr(p.price)}** per pack")
            in_cart = ss.cart.get(p.id, 0)
            at_limit = not p.sold_out and in_cart >= rules.max_qty(p)
            label = "Sold out" if p.sold_out else (f"{in_cart} in cart" if at_limit else
                                                   ("Add another" if in_cart else "Add to cart"))
            st.button(label, key=f"add_{p.id}", width="stretch", disabled=p.sold_out or at_limit,
                      on_click=add_to_cart, args=(p.id,))
            b1, b2 = st.columns(2)
            if b1.button("Details", key=f"view_{p.id}", width="stretch"):
                quick_view(p.id)
            saved = p.id in ss.wishlist
            b2.button(":material/favorite:" if saved else ":material/favorite_border:", key=f"wish_{p.id}",
                      help="Remove from saved" if saved else "Save for later", width="stretch",
                      on_click=toggle_wish, args=(p.id,))

if ss.recent:
    st.subheader("Recently viewed", anchor=False)
    for col, pid in zip(st.columns(4), ss.recent):
        x = BY_ID[pid]
        col.image(x.image_path, width=96)
        col.markdown(f"**{x.name}**  \n{rules.inr(x.price)}")
st.divider()

# ---------------------------------------------------------------- delivery check
st.header("Check delivery to your pincode")
st.write("We deliver within India in 2 to 5 working days, depending on where you are.")
with st.form("pin_form", border=True, enter_to_submit=True):
    pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
    pin = pc1.text_input("Your 6-digit pincode", max_chars=6, key="pin")
    submitted = pc2.form_submit_button("Check", width="stretch", key="pin_check")
if submitted:
    pin = pin.strip()
    if not pin:
        st.error("Enter your 6-digit pincode, for example 734001.", icon=":material/error:")
    else:
        try:
            with st.spinner(f"Checking {pin}…"):
                result = api.check_pincode(pin)
            if result["serviceable"]:
                d = result["days"]
                st.success(f"We deliver to {pin}. Estimated delivery: {d} day{'s' if d != 1 else ''}.",
                           icon=":material/check_circle:")
            else:
                st.warning(f"Sorry, {pin} is not serviceable yet.", icon=":material/location_off:")
        except api.InvalidPincode:
            st.error(f"“{pin}” is not a valid pincode. Indian pincodes have 6 digits and do not start with 0.",
                     icon=":material/error:")
        except Exception:
            st.error("We could not check delivery right now. Please try again.", icon=":material/error:")
st.divider()

# ---------------------------------------------------------------- reviews
st.header("What tea drinkers say")
for col, (quote, name, city) in zip(st.columns(3), REVIEWS):
    with col, st.container(border=True, height="stretch"):
        st.markdown(f"> {quote}")
        st.caption(f"**{name}**, {city}")
st.divider()

# ---------------------------------------------------------------- FAQ
st.header("Questions, answered")
for q, a in FAQ:
    with st.expander(q):
        st.write(a)
st.divider()

# ---------------------------------------------------------------- newsletter
st.header("Stay in touch")
st.write(f"Sign up for emails from {COMPANY['name']}, or follow us on [Instagram]({COMPANY['instagram']}).")
if ss.nl_email:
    st.success(f"Thank you for signing up with {ss.nl_email}.", icon=":material/check_circle:")
else:
    with st.form("newsletter", border=True, enter_to_submit=True):
        n1, n2 = st.columns([3, 1], vertical_alignment="bottom")
        email = n1.text_input("Email address")
        if n2.form_submit_button("Subscribe", type="primary", width="stretch"):
            if EMAIL_RE.match(email.strip()):
                ss.nl_email = email.strip()
                st.rerun()
            else:
                st.error("Please enter a full email address, like name@example.com."
                         if email.strip() else "Please enter your email address.")
st.divider()

# ---------------------------------------------------------------- footer
c1, c2, c3 = st.columns([1.4, 1, 1])
with c1:
    st.image(str(IMAGES / "logo.svg"), width=160)
    st.caption(COMPANY["tagline"])
with c2:
    st.markdown("**Contact**")
    st.caption(f"{COMPANY['name']}  \n{COMPANY['address']}  \n{COMPANY['phone']}  \n{COMPANY['email']}")
with c3:
    st.markdown("**Explore**")
    st.markdown(f"[Shop the teas](#our-teas)  \n[Delivery check](#check-delivery-to-your-pincode)  \n"
                f"[FAQ](#questions-answered)  \n[Instagram]({COMPANY['instagram']})")
st.caption(LEGAL)
st.caption(COPYRIGHT)
