# estyecomapp/management/commands/populate_baby.py
from django.core.management.base import BaseCommand
from estyecomapp.models import BabySubCategory, BabyItem


SUBCATEGORIES = [
    {"name": "Baby Clothes",       "order": 1,  "description": "Personalised and adorable outfits for newborns and toddlers",         "image_url": "https://images.unsplash.com/photo-1522771930-78848d9293e8?w=400&h=400&fit=crop"},
    {"name": "Nursery Decor",      "order": 2,  "description": "Dreamy wall art, mobiles and decorative accents for baby's room",      "image_url": "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=400&h=400&fit=crop"},
    {"name": "Baby Toys",          "order": 3,  "description": "Soft toys, rattles and sensory play items to stimulate little minds",   "image_url": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop"},
    {"name": "Cot Bedding",        "order": 4,  "description": "Cosy blankets, sheets and quilts for a safe and snug night's sleep",   "image_url": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=400&h=400&fit=crop"},
    {"name": "Nursery Furniture",  "order": 5,  "description": "Handcrafted cribs, shelving and storage to complete the nursery",      "image_url": "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=400&h=400&fit=crop"},
    {"name": "Baby Care",          "order": 6,  "description": "Natural bath-time essentials, gift sets and gentle skincare for babies","image_url": "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=400&h=400&fit=crop"},
    {"name": "Baby Gifts",         "order": 7,  "description": "Thoughtful hampers, keepsakes and new baby gift sets",                 "image_url": "https://images.unsplash.com/photo-1545558014-8692077e9b5c?w=400&h=400&fit=crop"},
    {"name": "Baby Accessories",   "order": 8,  "description": "Bibs, dummies, changing mats and all the little extras",              "image_url": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=400&fit=crop"},
    {"name": "Baby Shower",        "order": 9,  "description": "Decorations, invitations and favours to celebrate the new arrival",    "image_url": "https://images.unsplash.com/photo-1544776193-352d25ca82cd?w=400&h=400&fit=crop"},
    {"name": "Nappies & Changing", "order": 10, "description": "Eco-friendly nappies, changing bags and waterproof essentials",        "image_url": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop"},
    {"name": "Feeding",            "order": 11, "description": "Handmade bibs, weaning sets and personalised plates and bowls",        "image_url": "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=400&h=400&fit=crop"},
    {"name": "Baby Keepsakes",     "order": 12, "description": "Fingerprint kits, birth prints and memory boxes to treasure forever",  "image_url": "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=400&h=400&fit=crop"},
]

ITEMS = [
    # ── Baby Clothes ──────────────────────────────────────────────────────────
    {
        "sub": "Baby Clothes", "title": "Custom Embroidered New Best Friend Bodysuit with Dog or Cat",
        "price_usd": 17.48, "original_price": 56.39, "discount_pct": 69,
        "image_url": "https://images.unsplash.com/photo-1522771930-78848d9293e8?w=600&h=600&fit=crop",
        "shop_name": "TinyThreadsCo", "star_rating": 5.0, "review_count": 839,
        "is_star_seller": True, "is_ad": True, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "United States",
    },
    {
        "sub": "Baby Clothes", "title": "Custom Embroidered Youth Hoodie with Pet Portrait — Any Breed",
        "price_usd": 29.25, "original_price": 43.65, "discount_pct": 33,
        "image_url": "https://images.unsplash.com/photo-1522771930-78848d9293e8?w=600&h=600&fit=crop&sig=2",
        "shop_name": "PetPortraitWear", "star_rating": 5.0, "review_count": 912,
        "is_star_seller": True, "is_ad": True, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "United Kingdom",
    },
    {
        "sub": "Baby Clothes", "title": "Protected By Dog Siblings Bodysuit — Custom Name Baby Romper",
        "price_usd": 11.78, "original_price": 14.72, "discount_pct": 20,
        "image_url": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=600&h=600&fit=crop",
        "shop_name": "PawPrintBabies", "star_rating": 5.0, "review_count": 1146,
        "is_star_seller": True, "is_ad": True, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "FREE delivery", "low_stock_message": "", "shop_country": "United States",
    },

    # ── Nursery Decor ─────────────────────────────────────────────────────────
    {
        "sub": "Nursery Decor", "title": "Polka Dot Nursery Wallpaper — Peel & Stick Removable Dots for Baby Room",
        "price_usd": 24.99, "original_price": 34.99, "discount_pct": 28,
        "image_url": "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=600&h=600&fit=crop",
        "shop_name": "WallWondersCo", "star_rating": 4.8, "review_count": 2340,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "", "low_stock_message": "", "shop_country": "United States",
    },
    {
        "sub": "Nursery Decor", "title": "Personalised Name Sign — LED Light Up Letters for Nursery Wall",
        "price_usd": 38.00, "original_price": 55.00, "discount_pct": 31,
        "image_url": "https://images.unsplash.com/photo-1544776193-352d25ca82cd?w=600&h=600&fit=crop",
        "shop_name": "GlowNursery", "star_rating": 5.0, "review_count": 1820,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "United Kingdom",
    },

    # ── Baby Toys ─────────────────────────────────────────────────────────────
    {
        "sub": "Baby Toys", "title": "Handmade Floppy Eared Bunny Plush — Personalised Heirloom Soft Toy",
        "price_usd": 22.50, "original_price": 30.00, "discount_pct": 25,
        "image_url": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&h=600&fit=crop",
        "shop_name": "PlushPalsCo", "star_rating": 5.0, "review_count": 4290,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "FREE delivery", "low_stock_message": "", "shop_country": "Ireland",
    },
    {
        "sub": "Baby Toys", "title": "Duo Diner Custom Cover in Dinosaurs — Learning Placemat for Toddlers",
        "price_usd": 49.00, "original_price": None, "discount_pct": 0,
        "image_url": "https://images.unsplash.com/photo-1563396983906-b3795482a59a?w=600&h=600&fit=crop",
        "shop_name": "DinoTableCo", "star_rating": 5.0, "review_count": 1430,
        "is_star_seller": True, "is_ad": True, "has_free_delivery": False,
        "is_on_sale": False, "is_personalised": True,
        "badge_label": "", "low_stock_message": "Only 2 left – order soon", "shop_country": "United States",
    },
    {
        "sub": "Baby Toys", "title": "August with Rose Sunflower Plush — Handmade Floral Stuffed Animal",
        "price_usd": 26.00, "original_price": 35.00, "discount_pct": 26,
        "image_url": "https://images.unsplash.com/photo-1508766917616-d22f3f1eea14?w=600&h=600&fit=crop",
        "shop_name": "BloomBuddies", "star_rating": 4.9, "review_count": 3120,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "", "low_stock_message": "", "shop_country": "Netherlands",
    },
    {
        "sub": "Baby Toys", "title": "Flower Crown Kawaii Plush Eyes Doll — Handmade Soft Toy for Babies",
        "price_usd": 18.99, "original_price": 27.99, "discount_pct": 32,
        "image_url": "https://images.unsplash.com/photo-1599030822578-ab04cfa5a5a6?w=600&h=600&fit=crop",
        "shop_name": "KawaiiCraftCo", "star_rating": 4.8, "review_count": 876,
        "is_star_seller": False, "is_ad": False, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "", "low_stock_message": "", "shop_country": "Japan",
    },

    # ── Cot Bedding ───────────────────────────────────────────────────────────
    {
        "sub": "Cot Bedding", "title": "Personalised Knitted Baby Blanket — Name Embroidered Merino Wool Throw",
        "price_usd": 44.00, "original_price": 62.00, "discount_pct": 29,
        "image_url": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=600&h=600&fit=crop&sig=3",
        "shop_name": "KnitNestCo", "star_rating": 5.0, "review_count": 3710,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "FREE delivery", "low_stock_message": "", "shop_country": "United Kingdom",
    },
    {
        "sub": "Cot Bedding", "title": "Organic Cotton Muslin Swaddle Blanket Set of 3 — Woodland Animal Print",
        "price_usd": 32.00, "original_price": 45.00, "discount_pct": 29,
        "image_url": "https://images.unsplash.com/photo-1488751045188-3c55bbf9a3fa?w=600&h=600&fit=crop",
        "shop_name": "PureMuslinCo", "star_rating": 4.9, "review_count": 2455,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "", "low_stock_message": "", "shop_country": "Turkey",
    },

    # ── Nursery Furniture ─────────────────────────────────────────────────────
    {
        "sub": "Nursery Furniture", "title": "Personalized Wooden Name Crib Mobile — Engraved Animal Shapes",
        "price_usd": 55.00, "original_price": 75.00, "discount_pct": 27,
        "image_url": "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=600&h=600&fit=crop",
        "shop_name": "WoodenWondersCo", "star_rating": 5.0, "review_count": 1980,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "Canada",
    },
    {
        "sub": "Nursery Furniture", "title": "Boho Macramé Nursery Shelf — Floating Wall Shelf with Storage Basket",
        "price_usd": 48.00, "original_price": 65.00, "discount_pct": 26,
        "image_url": "https://images.unsplash.com/photo-1567016376408-0226e1d3d0c6?w=600&h=600&fit=crop",
        "shop_name": "KnotShelveCo", "star_rating": 4.9, "review_count": 1240,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "", "low_stock_message": "", "shop_country": "Portugal",
    },

    # ── Baby Care ─────────────────────────────────────────────────────────────
    {
        "sub": "Baby Care", "title": "Natural Organic Baby Gift Set — Lavender Bath Wash, Lotion & Balm",
        "price_usd": 36.00, "original_price": 50.00, "discount_pct": 28,
        "image_url": "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=600&h=600&fit=crop",
        "shop_name": "PureNatureCare", "star_rating": 5.0, "review_count": 2870,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": False,
        "badge_label": "FREE delivery", "low_stock_message": "", "shop_country": "France",
    },
    {
        "sub": "Baby Care", "title": "Personalised Baby Beach Toy Drawstring Bag — Custom Name Canvas Pouch",
        "price_usd": 14.99, "original_price": 19.99, "discount_pct": 25,
        "image_url": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=600&h=600&fit=crop",
        "shop_name": "BeachBabyShop", "star_rating": 4.9, "review_count": 1560,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": False,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "Australia",
    },

    # ── Baby Gifts ────────────────────────────────────────────────────────────
    {
        "sub": "Baby Gifts", "title": "New Baby Gift Hamper — Personalised Keepsake Box with Soft Toy & Outfit",
        "price_usd": 68.00, "original_price": 95.00, "discount_pct": 28,
        "image_url": "https://images.unsplash.com/photo-1545558014-8692077e9b5c?w=600&h=600&fit=crop",
        "shop_name": "GiftNestCo", "star_rating": 5.0, "review_count": 4130,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True,
        "is_on_sale": True, "is_personalised": True,
        "badge_label": "", "low_stock_message": "", "shop_country": "United Kingdom",
    },
]


class Command(BaseCommand):
    help = "Populate Baby sub-categories and products with seed data"

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing baby data …")
        BabyItem.objects.all().delete()
        BabySubCategory.objects.all().delete()

        self.stdout.write("Creating sub-categories …")
        cat_map = {}
        for sc in SUBCATEGORIES:
            obj = BabySubCategory.objects.create(**sc)
            cat_map[sc["name"]] = obj
            self.stdout.write(f"  ✓ {obj.name}")

        self.stdout.write("Creating products …")
        for item_data in ITEMS:
            sub_name = item_data.pop("sub")
            sub = cat_map.get(sub_name)
            BabyItem.objects.create(sub_category=sub, **item_data)
            self.stdout.write(f"  ✓ {item_data['title'][:60]}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {BabySubCategory.objects.count()} sub-categories, "
            f"{BabyItem.objects.count()} products."
        ))