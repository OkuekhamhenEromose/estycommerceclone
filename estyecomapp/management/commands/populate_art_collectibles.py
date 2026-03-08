# estyecomapp/management/commands/populate_art_collectibles.py
# Run: python manage.py populate_art_collectibles

from django.core.management.base import BaseCommand
from estyecomapp.models import ArtSubCategory, ArtItem


SUBCATEGORIES = [
    {
        "name":        "Prints",
        "description": "Art prints, posters and wall art for every style",
        "image_url":   "https://images.unsplash.com/photo-1578926375605-eaf7559b1458?w=400&h=400&fit=crop",
        "order":       1,
    },
    {
        "name":        "Painting",
        "description": "Original oil, watercolour and acrylic paintings",
        "image_url":   "https://images.unsplash.com/photo-1579762715118-a6f1d4b934f1?w=400&h=400&fit=crop",
        "order":       2,
    },
    {
        "name":        "Sculpture",
        "description": "Handcrafted sculptures in clay, metal, wood and more",
        "image_url":   "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop",
        "order":       3,
    },
    {
        "name":        "Glass Art",
        "description": "Stained glass, fused glass and blown glass pieces",
        "image_url":   "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=400&fit=crop",
        "order":       4,
    },
    {
        "name":        "Fine Art Ceramics",
        "description": "Hand-thrown pottery, vessels and sculptural ceramics",
        "image_url":   "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=400&h=400&fit=crop",
        "order":       5,
    },
    {
        "name":        "Collectibles",
        "description": "Vintage finds, figurines and rare collectible items",
        "image_url":   "https://images.unsplash.com/photo-1608848461950-0fe51dfc41cb?w=400&h=400&fit=crop",
        "order":       6,
    },
    {
        "name":        "Drawing & Illustration",
        "description": "Original drawings, illustrations and sketches",
        "image_url":   "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=400&h=400&fit=crop",
        "order":       7,
    },
    {
        "name":        "Photography",
        "description": "Fine art photography prints and limited editions",
        "image_url":   "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=400&fit=crop",
        "order":       8,
    },
    {
        "name":        "Fibre Arts",
        "description": "Macramé, weaving, tapestry and textile art",
        "image_url":   "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=400&h=400&fit=crop",
        "order":       9,
    },
    {
        "name":        "Dolls & Miniatures",
        "description": "Handmade dolls, plushies and miniature scenes",
        "image_url":   "https://images.unsplash.com/photo-1563396983906-b3795482a59a?w=400&h=400&fit=crop",
        "order":       10,
    },
    {
        "name":        "Mixed Media & Collage",
        "description": "Multi-medium artworks combining paint, paper and more",
        "image_url":   "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=400&h=400&fit=crop",
        "order":       11,
    },
    {
        "name":        "Artist Trading Cards",
        "description": "Collectible mini artworks in standard card format",
        "image_url":   "https://images.unsplash.com/photo-1522542550221-31fd19575a2d?w=400&h=400&fit=crop",
        "order":       12,
    },
]

PRODUCTS = [
    # ── Prints ─────────────────────────────────────────────────────────────────
    {
        "sub_category_name": "Prints",
        "title":        "Fierce Wolves Face SVG | School Spirit Graphic | Digital Download",
        "price_usd":    3.37,
        "original_price": 3.75,
        "discount_pct": 10,
        "image_url":    "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=600&h=600&fit=crop",
        "shop_name":    "DigitalDenDesigns",
        "star_rating":  5.0,
        "review_count": 2990,
        "is_star_seller":      True,
        "is_ad":               True,
        "has_free_delivery":   False,
        "is_digital_download": True,
        "shop_country": "United States",
        "badge_label":  "Digital Download",
    },
    {
        "sub_category_name": "Prints",
        "title":        "Tulip 2 — Fine Art Botanical Print, Pastel Flower Wall Art",
        "price_usd":    100.00,
        "original_price": None,
        "discount_pct": 0,
        "image_url":    "https://images.unsplash.com/photo-1490750967868-88df5691b71e?w=600&h=600&fit=crop",
        "shop_name":    "BloomPrintCo",
        "star_rating":  4.8,
        "review_count": 312,
        "is_star_seller":      False,
        "is_ad":               True,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "United Kingdom",
        "badge_label":  "",
    },
    # ── Painting ───────────────────────────────────────────────────────────────
    {
        "sub_category_name": "Painting",
        "title":        "Add Loved One to Photo — Memorial Portrait, Custom Family Painting",
        "price_usd":    21.90,
        "original_price": 43.80,
        "discount_pct": 50,
        "image_url":    "https://images.unsplash.com/photo-1604480132736-44c188fe4d20?w=600&h=600&fit=crop",
        "shop_name":    "PortraitsByAna",
        "star_rating":  5.0,
        "review_count": 6736,
        "is_star_seller":      True,
        "is_ad":               True,
        "has_free_delivery":   False,
        "is_digital_download": True,
        "shop_country": "United States",
        "badge_label":  "Digital Download",
    },
    {
        "sub_category_name": "Painting",
        "title":        "Hand-Painted Green Leaves Oil Painting — Tropical Botanical Canvas",
        "price_usd":    142.50,
        "original_price": 190.00,
        "discount_pct": 25,
        "image_url":    "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?w=600&h=600&fit=crop",
        "shop_name":    "LeafStudioArt",
        "star_rating":  4.5,
        "review_count": 74,
        "is_star_seller":      False,
        "is_ad":               True,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "France",
        "badge_label":  "FREE delivery",
    },
    # ── Collectibles ──────────────────────────────────────────────────────────
    {
        "sub_category_name": "Collectibles",
        "title":        "Animal Crossing Character Button Pins Set — Cute Collectible Fan Art",
        "price_usd":    8.50,
        "original_price": 12.00,
        "discount_pct": 29,
        "image_url":    "https://images.unsplash.com/photo-1608848461950-0fe51dfc41cb?w=600&h=600&fit=crop",
        "shop_name":    "PinPalaceShop",
        "star_rating":  5.0,
        "review_count": 4821,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "Canada",
        "badge_label":  "",
    },
    {
        "sub_category_name": "Collectibles",
        "title":        "Pokémon Kawaii Sticker Sheet — 48 Holographic Mini Character Stickers",
        "price_usd":    5.99,
        "original_price": 7.99,
        "discount_pct": 25,
        "image_url":    "https://images.unsplash.com/photo-1610296669228-602fa827fc1f?w=600&h=600&fit=crop",
        "shop_name":    "KawaiiFanArt",
        "star_rating":  4.9,
        "review_count": 3150,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "Japan",
        "badge_label":  "",
    },
    {
        "sub_category_name": "Collectibles",
        "title":        "Friends TV Show Figurine Set — Central Perk Sofa Diorama Collectible",
        "price_usd":    34.00,
        "original_price": 48.00,
        "discount_pct": 29,
        "image_url":    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=600&fit=crop",
        "shop_name":    "FanFigurines",
        "star_rating":  4.8,
        "review_count": 1290,
        "is_star_seller":      False,
        "is_ad":               False,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "United States",
        "badge_label":  "",
    },
    # ── Sculpture ────────────────────────────────────────────────────────────
    {
        "sub_category_name": "Sculpture",
        "title":        "Handmade White Butterfly Paper Sculpture — 3D Wall Art Installation",
        "price_usd":    55.00,
        "original_price": 75.00,
        "discount_pct": 27,
        "image_url":    "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=600&h=600&fit=crop",
        "shop_name":    "PaperWingsArt",
        "star_rating":  4.9,
        "review_count": 823,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "Netherlands",
        "badge_label":  "",
    },
    # ── Glass Art ─────────────────────────────────────────────────────────────
    {
        "sub_category_name": "Glass Art",
        "title":        "Sunset Desert Stained Glass Panel — Handcut Lead & Copper Foil Art",
        "price_usd":    89.00,
        "original_price": 120.00,
        "discount_pct": 26,
        "image_url":    "https://images.unsplash.com/photo-1560448205-4d9b3e6bb6db?w=600&h=600&fit=crop",
        "shop_name":    "GlassGroveCraft",
        "star_rating":  5.0,
        "review_count": 540,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "United States",
        "badge_label":  "",
    },
    # ── Fine Art Ceramics ────────────────────────────────────────────────────
    {
        "sub_category_name": "Fine Art Ceramics",
        "title":        "Handthrown Speckled Cat & Fox Stoneware Mug Pair — Woodland Ceramics",
        "price_usd":    48.00,
        "original_price": 65.00,
        "discount_pct": 26,
        "image_url":    "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=600&h=600&fit=crop",
        "shop_name":    "WoodlandKilns",
        "star_rating":  5.0,
        "review_count": 2104,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "Ireland",
        "badge_label":  "",
    },
    # ── Drawing & Illustration ───────────────────────────────────────────────
    {
        "sub_category_name": "Drawing & Illustration",
        "title":        "Custom Family Portrait — Illustrated Character Style, Digital File",
        "price_usd":    18.00,
        "original_price": 30.00,
        "discount_pct": 40,
        "image_url":    "https://images.unsplash.com/photo-1453733190371-0a9bedd82893?w=600&h=600&fit=crop",
        "shop_name":    "ToonFamilyArt",
        "star_rating":  5.0,
        "review_count": 8910,
        "is_star_seller":      True,
        "is_ad":               True,
        "has_free_delivery":   False,
        "is_digital_download": True,
        "shop_country": "United Kingdom",
        "badge_label":  "Digital Download",
    },
    # ── Photography ──────────────────────────────────────────────────────────
    {
        "sub_category_name": "Photography",
        "title":        "Mountain Sunrise Fine Art Photography Print — Misty Alps at Dawn",
        "price_usd":    35.00,
        "original_price": 50.00,
        "discount_pct": 30,
        "image_url":    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=600&fit=crop",
        "shop_name":    "AlpsLensStudio",
        "star_rating":  4.8,
        "review_count": 670,
        "is_star_seller":      False,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "Switzerland",
        "badge_label":  "",
    },
    # ── Fibre Arts ───────────────────────────────────────────────────────────
    {
        "sub_category_name": "Fibre Arts",
        "title":        "Boho Macramé Wall Hanging with Fringe — Large Woven Tapestry for Living Room",
        "price_usd":    62.00,
        "original_price": 85.00,
        "discount_pct": 27,
        "image_url":    "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=600&h=600&fit=crop",
        "shop_name":    "KnotAndWeave",
        "star_rating":  4.9,
        "review_count": 3300,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "Portugal",
        "badge_label":  "",
    },
    # ── Dolls & Miniatures ───────────────────────────────────────────────────
    {
        "sub_category_name": "Dolls & Miniatures",
        "title":        "Handmade Soft Body Bunny Doll in Vintage Floral Dress — Heirloom Toy",
        "price_usd":    29.00,
        "original_price": 42.00,
        "discount_pct": 31,
        "image_url":    "https://images.unsplash.com/photo-1563396983906-b3795482a59a?w=600&h=600&fit=crop",
        "shop_name":    "HeirloomDolls",
        "star_rating":  5.0,
        "review_count": 1870,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "United Kingdom",
        "badge_label":  "",
    },
    # ── Mixed Media & Collage ────────────────────────────────────────────────
    {
        "sub_category_name": "Mixed Media & Collage",
        "title":        "Abstract Mixed Media Portrait on Canvas — Layered Collage Original",
        "price_usd":    120.00,
        "original_price": 165.00,
        "discount_pct": 27,
        "image_url":    "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=600&h=600&fit=crop",
        "shop_name":    "LayeredSoulArt",
        "star_rating":  4.9,
        "review_count": 445,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   True,
        "is_digital_download": False,
        "shop_country": "France",
        "badge_label":  "",
    },
    # ── Artist Trading Cards ─────────────────────────────────────────────────
    {
        "sub_category_name": "Artist Trading Cards",
        "title":        "Galaxy & Cosmos Artist Trading Card Set of 10 — Original Mini Paintings",
        "price_usd":    22.00,
        "original_price": 30.00,
        "discount_pct": 27,
        "image_url":    "https://images.unsplash.com/photo-1522542550221-31fd19575a2d?w=600&h=600&fit=crop",
        "shop_name":    "CosmicATCShop",
        "star_rating":  5.0,
        "review_count": 987,
        "is_star_seller":      True,
        "is_ad":               False,
        "has_free_delivery":   False,
        "is_digital_download": False,
        "shop_country": "United States",
        "badge_label":  "",
    },
]


class Command(BaseCommand):
    help = "Populate Art & Collectibles sub-categories and products"

    def handle(self, *args, **options):
        sep = "═" * 55
        self.stdout.write(f"\n{sep}")
        self.stdout.write("  Populating Art & Collectibles …")
        self.stdout.write(f"{sep}\n")

        # ── Sub-categories ────────────────────────────────────
        self.stdout.write("\n📂 Sub-categories:")
        cat_map = {}
        for data in SUBCATEGORIES:
            obj, created = ArtSubCategory.objects.get_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "image_url":   data["image_url"],
                    "order":       data["order"],
                    "is_active":   True,
                }
            )
            cat_map[data["name"]] = obj
            label = "✅  created" if created else "⏭   exists"
            self.stdout.write(f"  {label}  {obj.name}")

        # ── Products ──────────────────────────────────────────
        self.stdout.write("\n🏷  Products:")
        created_count = 0
        skipped_count = 0

        for data in PRODUCTS:
            cat = cat_map.get(data["sub_category_name"])
            if not cat:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Unknown sub_category: {data['sub_category_name']}"
                    )
                )
                continue

            obj, created = ArtItem.objects.get_or_create(
                title=data["title"],
                defaults={
                    "sub_category":        cat,
                    "price_usd":           data["price_usd"],
                    "original_price":      data.get("original_price"),
                    "discount_pct":        data.get("discount_pct", 0),
                    "image_url":           data["image_url"],
                    "shop_name":           data.get("shop_name", ""),
                    "star_rating":         data.get("star_rating", 0.0),
                    "review_count":        data.get("review_count", 0),
                    "is_star_seller":      data.get("is_star_seller", False),
                    "is_ad":               data.get("is_ad", False),
                    "has_free_delivery":   data.get("has_free_delivery", False),
                    "is_digital_download": data.get("is_digital_download", False),
                    "badge_label":         data.get("badge_label", ""),
                    "shop_country":        data.get("shop_country", "Anywhere"),
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"  ✅  {obj.title[:65]}")
            else:
                skipped_count += 1
                self.stdout.write(f"  ⏭   {obj.title[:65]}")

        self.stdout.write(f"\n{sep}")
        self.stdout.write(
            self.style.SUCCESS(
                f"  Done — {created_count} created, {skipped_count} skipped."
            )
        )
        self.stdout.write(f"{sep}\n")