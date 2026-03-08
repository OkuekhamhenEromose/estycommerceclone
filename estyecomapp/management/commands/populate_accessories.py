# estyecomapp/management/commands/populate_accessories.py
"""
Run with:
    python manage.py populate_accessories

Creates all 12 AccessorySubCategory records and 16 AccessoryItem
seed products that exactly match the Etsy Accessories page screenshots.
"""
from django.core.management.base import BaseCommand
from estyecomapp.models import AccessorySubCategory, AccessoryItem
from decimal import Decimal


SUBCATEGORIES = [
    {
        "name": "Hair Accessories", "order": 1,
        "image_url": "https://images.unsplash.com/photo-1616598271627-421debb58794?w=400&h=400&fit=crop",
        "description": "Headbands, clips, scrunchies and more",
    },
    {
        "name": "Patches & Appliques", "order": 2,
        "image_url": "https://images.unsplash.com/photo-1589810264340-0ce2b6b96a7e?w=400&h=400&fit=crop",
        "description": "Iron-on and sew-on patches for clothes",
    },
    {
        "name": "Scarves & Wraps", "order": 3,
        "image_url": "https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=400&h=400&fit=crop",
        "description": "Silk, wool and cotton scarves",
    },
    {
        "name": "Hats & Head Coverings", "order": 4,
        "image_url": "https://images.unsplash.com/photo-1533055640609-24b498dfd74c?w=400&h=400&fit=crop",
        "description": "Beanies, caps, turbans and more",
    },
    {
        "name": "Pins & Clips", "order": 5,
        "image_url": "https://images.unsplash.com/photo-1583394293214-0d8b4948f5d0?w=400&h=400&fit=crop",
        "description": "Enamel pins, brooches and clips",
    },
    {
        "name": "Keychains & Lanyards", "order": 6,
        "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop",
        "description": "Custom keyrings and badge holders",
    },
    {
        "name": "Belts & Braces", "order": 7,
        "image_url": "https://images.unsplash.com/photo-1624627314873-3fc96a1ec877?w=400&h=400&fit=crop",
        "description": "Leather belts, suspenders and more",
    },
    {
        "name": "Suit & Tie", "order": 8,
        "image_url": "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400&h=400&fit=crop",
        "description": "Ties, cufflinks, pocket squares",
    },
    {
        "name": "Sunglasses & Eyewear", "order": 9,
        "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop",
        "description": "Fashion frames and reading glasses",
    },
    {
        "name": "Bouquets & Corsages", "order": 10,
        "image_url": "https://images.unsplash.com/photo-1490750967868-88df5691b71e?w=400&h=400&fit=crop",
        "description": "Dried and fresh floral accessories",
    },
    {
        "name": "Costume Accessories", "order": 11,
        "image_url": "https://images.unsplash.com/photo-1605291286356-50a6fb5f2b7c?w=400&h=400&fit=crop",
        "description": "Props, masks and dress-up extras",
    },
    {
        "name": "Aprons", "order": 12,
        "image_url": "https://images.unsplash.com/photo-1582719471384-894fbb16e074?w=400&h=400&fit=crop",
        "description": "Kitchen and craft aprons",
    },
]

ITEMS = [
    # ── Screenshot products (exact match) ────────────────
    {
        "sub_category": "Hats & Head Coverings",
        "title":         "Custom Embroidered Pet Photo Dad Hat",
        "price_usd":     "8.00",  "original_price": "19.99", "discount_pct": 60,
        "image_url":     "https://images.unsplash.com/photo-1533055640609-24b498dfd74c?w=600&h=600&fit=crop",
        "shop_name":     "ODPAWS", "star_rating": "5.0", "review_count": 70299,
        "is_star_seller": False, "is_ad": True, "badge_label": "SHIPS FROM USA",
        "shop_country":  "United States",
    },
    {
        "sub_category": "Suit & Tie",
        "title":         "Mens Personalized Embroidered Pocket Square",
        "price_usd":     "9.90",  "original_price": "19.80", "discount_pct": 50,
        "image_url":     "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=600&h=600&fit=crop",
        "shop_name":     "PatchPerfect", "star_rating": "5.0", "review_count": 74,
        "is_star_seller": True, "is_ad": True, "badge_label": "",
        "shop_country":  "United States",
    },
    {
        "sub_category": "Keychains & Lanyards",
        "title":         "Personalised Photo Keyring | Custom Picture with Gift Box",
        "price_usd":     "6.83",  "original_price": "9.11",  "discount_pct": 25,
        "image_url":     "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=600&fit=crop",
        "shop_name":     "KeyMemories", "star_rating": "5.0", "review_count": 149,
        "is_star_seller": False, "is_ad": True, "badge_label": "",
        "shop_country":  "United Kingdom",
    },
    {
        "sub_category": "Hats & Head Coverings",
        "title":         "US 250th Anniversary Distressed Baseball Cap 1776–2026",
        "price_usd":     "15.79", "original_price": "31.58", "discount_pct": 50,
        "image_url":     "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=600&h=600&fit=crop",
        "shop_name":     "PatriotGear", "star_rating": "4.5", "review_count": 5,
        "is_star_seller": False, "is_ad": True, "badge_label": "",
        "shop_country":  "United States",
    },
    {
        "sub_category": "Scarves & Wraps",
        "title":         "Embroidered Sleeping Fox Umbrella — Woodland Art Piece",
        "price_usd":     "42.99", "original_price": None, "discount_pct": 0,
        "image_url":     "https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=600&h=600&fit=crop",
        "shop_name":     "FoxWoodCraft", "star_rating": "4.5", "review_count": 1074,
        "is_star_seller": True, "is_ad": True, "badge_label": "",
        "shop_country":  "Japan",
    },
    {
        "sub_category": "Patches & Appliques",
        "title":         "CUSTOM Embroidered Patch – Up To 11\" – Iron On or Sew On",
        "price_usd":     "1.98",  "original_price": "4.40",  "discount_pct": 55,
        "image_url":     "https://images.unsplash.com/photo-1589810264340-0ce2b6b96a7e?w=600&h=600&fit=crop",
        "shop_name":     "EmbroideryKing", "star_rating": "5.0", "review_count": 21401,
        "is_star_seller": True, "is_ad": True, "badge_label": "",
        "shop_country":  "United States",
    },
    # ── Remaining catalogue ───────────────────────────────
    {
        "sub_category": "Hair Accessories",
        "title":         "Vintage Velvet Scrunchie Set — Jewel Tone Hair Ties",
        "price_usd":     "12.50", "original_price": "20.00", "discount_pct": 38,
        "image_url":     "https://images.unsplash.com/photo-1616598271627-421debb58794?w=600&h=600&fit=crop",
        "shop_name":     "VelvetBloom", "star_rating": "4.8", "review_count": 3412,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True, "badge_label": "",
        "shop_country":  "United Kingdom",
    },
    {
        "sub_category": "Belts & Braces",
        "title":         "Full-Grain Leather Dress Belt — Handstitched Cognac & Tan",
        "price_usd":     "38.00", "original_price": "55.00", "discount_pct": 31,
        "image_url":     "https://images.unsplash.com/photo-1624627314873-3fc96a1ec877?w=600&h=600&fit=crop",
        "shop_name":     "HideCraft", "star_rating": "4.8", "review_count": 789,
        "is_star_seller": True, "is_ad": False, "badge_label": "",
        "shop_country":  "Italy",
    },
    {
        "sub_category": "Sunglasses & Eyewear",
        "title":         "Handmade Acetate Cat-Eye Sunglasses — UV400 Vintage Retro",
        "price_usd":     "28.50", "original_price": "50.00", "discount_pct": 43,
        "image_url":     "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&h=600&fit=crop",
        "shop_name":     "FramedByHand", "star_rating": "4.7", "review_count": 930,
        "is_star_seller": False, "is_ad": False, "badge_label": "",
        "shop_country":  "Portugal",
    },
    {
        "sub_category": "Bouquets & Corsages",
        "title":         "Dried Flower Wedding Wrist Corsage — Bohemian Bridal Floral",
        "price_usd":     "22.00", "original_price": "35.00", "discount_pct": 37,
        "image_url":     "https://images.unsplash.com/photo-1490750967868-88df5691b71e?w=600&h=600&fit=crop",
        "shop_name":     "PetalAtelier", "star_rating": "5.0", "review_count": 612,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True, "badge_label": "",
        "shop_country":  "France",
    },
    {
        "sub_category": "Pins & Clips",
        "title":         "Custom Enamel Pin — Personalised Pet Portrait Hard Lapel Pin",
        "price_usd":     "11.00", "original_price": "15.00", "discount_pct": 27,
        "image_url":     "https://images.unsplash.com/photo-1583394293214-0d8b4948f5d0?w=600&h=600&fit=crop",
        "shop_name":     "PinForge", "star_rating": "4.9", "review_count": 2300,
        "is_star_seller": True, "is_ad": False, "badge_label": "",
        "shop_country":  "Canada",
    },
    {
        "sub_category": "Suit & Tie",
        "title":         "Personalized Wedding Tie — Custom Embroidered Initials Gift",
        "price_usd":     "22.00", "original_price": "35.00", "discount_pct": 37,
        "image_url":     "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=600&h=600&fit=crop",
        "shop_name":     "TheTieAtelier", "star_rating": "5.0", "review_count": 450,
        "is_star_seller": True, "is_ad": False, "badge_label": "",
        "shop_country":  "France",
    },
    {
        "sub_category": "Scarves & Wraps",
        "title":         "100% Cashmere Plaid Wrap Scarf — Oversized Scottish Tartan",
        "price_usd":     "34.00", "original_price": "58.00", "discount_pct": 41,
        "image_url":     "https://images.unsplash.com/photo-1543076447-215ad9ba6923?w=600&h=600&fit=crop",
        "shop_name":     "CashmereGlen", "star_rating": "4.9", "review_count": 5670,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True, "badge_label": "",
        "shop_country":  "United Kingdom",
    },
    {
        "sub_category": "Costume Accessories",
        "title":         "Steampunk Masquerade Mask — Halloween Costume Accessory Set",
        "price_usd":     "18.99", "original_price": "28.00", "discount_pct": 32,
        "image_url":     "https://images.unsplash.com/photo-1605291286356-50a6fb5f2b7c?w=600&h=600&fit=crop",
        "shop_name":     "MaskSmiths", "star_rating": "4.6", "review_count": 887,
        "is_star_seller": False, "is_ad": False, "badge_label": "",
        "shop_country":  "United States",
    },
    {
        "sub_category": "Aprons",
        "title":         "Personalised Linen Chef Apron — Custom Embroidered Name Gift",
        "price_usd":     "29.95", "original_price": "45.00", "discount_pct": 33,
        "image_url":     "https://images.unsplash.com/photo-1582719471384-894fbb16e074?w=600&h=600&fit=crop",
        "shop_name":     "KitchenStitch", "star_rating": "4.9", "review_count": 1203,
        "is_star_seller": True, "is_ad": False, "has_free_delivery": True, "badge_label": "",
        "shop_country":  "Ireland",
    },
    {
        "sub_category": "Hair Accessories",
        "title":         "Handmade Rattan Claw Clip — Boho Natural Fibre Large Clamp",
        "price_usd":     "9.95",  "original_price": "14.00", "discount_pct": 29,
        "image_url":     "https://images.unsplash.com/photo-1627552527750-38c8218c9503?w=600&h=600&fit=crop",
        "shop_name":     "BohoRoots", "star_rating": "4.9", "review_count": 1850,
        "is_star_seller": True, "is_ad": False, "badge_label": "",
        "shop_country":  "France",
    },
]


class Command(BaseCommand):
    help = "Populates AccessorySubCategory and AccessoryItem tables"

    def handle(self, *args, **options):
        self.stdout.write("═" * 55)
        self.stdout.write("  Populating Accessories …")
        self.stdout.write("═" * 55)

        # ── Sub-categories ────────────────────────────────
        self.stdout.write("\n📂 Sub-categories:")
        cat_map: dict[str, AccessorySubCategory] = {}
        for data in SUBCATEGORIES:
            cat, created = AccessorySubCategory.objects.get_or_create(
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "image_url":   data["image_url"],
                    "order":       data["order"],
                    "is_active":   True,
                },
            )
            cat_map[cat.name] = cat
            flag = "✅ created" if created else "⏭  exists "
            self.stdout.write(f"  {flag}  {cat.name}")

        # ── Items ─────────────────────────────────────────
        self.stdout.write("\n🏷  Products:")
        created_count = 0
        for data in ITEMS:
            sub = cat_map.get(data["sub_category"])
            if not sub:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠  Sub-category '{data['sub_category']}' not found — skipped")
                )
                continue

            _, created = AccessoryItem.objects.get_or_create(
                title=data["title"],
                defaults={
                    "sub_category":     sub,
                    "price_usd":        Decimal(data["price_usd"]),
                    "original_price":   Decimal(data["original_price"]) if data.get("original_price") else None,
                    "discount_pct":     data.get("discount_pct", 0),
                    "image_url":        data["image_url"],
                    "shop_name":        data.get("shop_name", ""),
                    "star_rating":      Decimal(str(data.get("star_rating", "0"))),
                    "review_count":     data.get("review_count", 0),
                    "is_star_seller":   data.get("is_star_seller", False),
                    "is_ad":            data.get("is_ad", False),
                    "has_free_delivery":data.get("has_free_delivery", False),
                    "badge_label":      data.get("badge_label", ""),
                    "shop_country":     data.get("shop_country", "Anywhere"),
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  ✅  {data['title'][:65]}")
            else:
                self.stdout.write(f"  ⏭   {data['title'][:65]}")

        self.stdout.write("\n" + "═" * 55)
        self.stdout.write(
            self.style.SUCCESS(
                f"  Done — {created_count} new products created.\n"
            )
        )