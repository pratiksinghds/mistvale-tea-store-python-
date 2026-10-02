"""Product catalogue and company facts. Prices are per pack and include GST."""
from dataclasses import dataclass
from pathlib import Path

IMAGES = Path(__file__).resolve().parent.parent / "images"


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    price: int          # rupees per pack, GST included
    stock: int
    image: str
    desc: str
    alt: str
    rating: float | None = None
    reviews: int | None = None

    @property
    def sold_out(self) -> bool:
        return self.stock <= 0

    @property
    def image_path(self) -> str:
        return str(IMAGES / self.image)


PRODUCTS: list[Product] = [
    Product(101, "Assam Breakfast Black Tea", "Black", 349, 40, "p101.webp",
            "Strong, malty CTC tea from Upper Assam estates. Perfect with milk and a little sugar in the morning.",
            "Mistvale kraft pouch of Assam Breakfast Black Tea beside a dish of dark, malty CTC granules"),
    Product(102, "Darjeeling First Flush", "Black", 1299, 12, "p102.webp",
            "Delicate, floral spring harvest leaves with a muscatel note. Best without milk.",
            "Mistvale kraft pouch of Darjeeling First Flush beside a dish of light, wiry spring leaves",
            rating=4.8, reviews=128),
    Product(103, "Kashmiri Kahwa", "Green", 549, 25, "p103.webp",
            "Green tea with saffron, cardamom, cinnamon and almond flakes.",
            "Mistvale kraft pouch of Kashmiri Kahwa beside a dish of green tea, saffron, cardamom, cinnamon and almond flakes"),
    Product(104, "Masala Chai Blend", "Black", 399, 60, "p104.webp",
            "Bold Assam leaves with ginger, cardamom, clove and black pepper. Our bestseller.",
            "Mistvale kraft pouch of Masala Chai Blend beside a dish of tea with ginger, cardamom, cloves and black pepper",
            rating=4.7, reviews=342),
    Product(105, "Nilgiri Green Tea", "Green", 449, 30, "p105.webp",
            "Smooth, grassy green tea from the Blue Mountains of the south.",
            "Mistvale kraft pouch of Nilgiri Green Tea beside a dish of rolled green leaves"),
    Product(106, "Chamomile & Tulsi", "Herbal", 499, 18, "p106.webp",
            "Caffeine-free calming blend of chamomile flowers and holy basil.",
            "Mistvale kraft pouch of Chamomile & Tulsi beside a dish of dried chamomile flowers and holy basil"),
    Product(107, "Hibiscus Rose Infusion", "Herbal", 599, 0, "p107.webp",
            "Tangy hibiscus with rose petals. Lovely iced.",
            "Mistvale kraft pouch of Hibiscus Rose Infusion beside a dish of dried hibiscus and rose petals"),
    Product(108, "Tea Lover's Sampler Gift Box", "Gifts", 1899, 9, "p108.webp",
            "Six of our favourite teas in a wooden gift box with a brewing guide.",
            "An open wooden Mistvale gift box with six small tea pouches and a folded brewing guide"),
]

BY_ID: dict[int, Product] = {p.id: p for p in PRODUCTS}
CATEGORY_LABEL = {"Black": "Black tea", "Green": "Green tea", "Herbal": "Herbal", "Gifts": "Gift box"}

COMPANY = {
    "name": "Mistvale Tea Co.",
    "tagline": "Hill-grown tea, honestly made.",
    "founded": 2019,
    "address": "14 Hill Cart Road, Siliguri, West Bengal 734001, India",
    "phone": "+91 90000 12345",
    "email": "hello@mistvale.example",
    "instagram": "https://instagram.com/mistvale.example",
}

FAQ = [
    ("How long does delivery take?", "2 to 5 working days depending on your pincode. Use the delivery check to see yours."),
    ("Can I return tea?", "Unopened packs can be returned within 7 days of delivery. Opened tea cannot be returned for hygiene reasons."),
    ("How should I store my tea?", "In an airtight container, away from light, heat and strong smells. It tastes best within 6 months of opening."),
    ("Is Chamomile & Tulsi caffeine-free?", "Yes, it is a caffeine-free herbal blend."),
    ("Do you ship outside India?", "Not yet. We currently deliver within India only."),
    ("Can I send tea as a gift?", "Yes. The Tea Lover's Sampler comes in a wooden gift box with a brewing guide."),
]

REVIEWS = [
    ("Best masala chai I have ever had. Tastes like my nani's kitchen.", "Ananya", "Pune"),
    ("The Darjeeling first flush is so fresh. Packaging was lovely too.", "Rohit", "Bengaluru"),
    ("Bought the sampler as a gift and now my whole family is hooked.", "Meera", "Kochi"),
]

# Approved wording - do not edit (ref MV-LGL-07)
LEGAL = (
    "All prices are inclusive of GST. Returns are accepted within 7 days of delivery on unopened packs only; "
    "opened tea cannot be returned for hygiene reasons. Tea colour and flavour may vary slightly between harvests."
)
COPYRIGHT = "© 2020 MistVale. All right reserved."
