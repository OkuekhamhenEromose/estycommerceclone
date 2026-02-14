from rest_framework import serializers
from django.core.cache import cache
from .models import *

# ========== COMPACT SERIALIZERS (Minimal fields, short keys) ==========
class CompactCategorySerializer(serializers.ModelSerializer):
    """Ultra-lightweight category serializer - 70% smaller payload"""
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'image']
    
    def to_representation(self, instance):
        return {
            'id': instance.id,
            't': instance.title[:40],  # Short field names save bandwidth
            's': instance.slug,
            'i': instance.image.url if instance.image else None,
        }

class CompactProductSerializer(serializers.ModelSerializer):
    """Ultra-lightweight product serializer for lists"""
    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'price', 'discount_price', 'main', 'rating', 'review_count']
    
    def to_representation(self, instance):
        final_price = instance.discount_price or instance.price
        discount = int(((instance.price - instance.discount_price) / instance.price * 100)) if instance.discount_price else 0
        
        return {
            'id': instance.id,
            't': instance.title[:50],
            's': instance.slug,
            'p': float(instance.price),
            'd': float(instance.discount_price) if instance.discount_price else None,
            'f': float(final_price),
            'dp': discount,
            'i': instance.main.url if instance.main else None,
            'r': float(instance.rating),
            'rc': instance.review_count,
        }

# ========== PRODUCT SIZE SERIALIZER ==========
class ProductSizeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = ProductSize
        fields = ['id', 'category', 'category_display', 'name', 'code', 'order']

# ========== PARENT CATEGORY SERIALIZER ==========
class ParentCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'order', 'is_active', 'is_featured', 'product_count']
    
    def get_product_count(self, obj):
        # Try cache first
        cache_key = f'parent:cat:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.get_product_count()
            cache.set(cache_key, count, 3600)
        return count

# ========== CATEGORY SERIALIZERS ==========
class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for category lists"""
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'title', 'slug', 'category_type', 'image', 
            'icon', 'order', 'is_active', 'is_featured', 'products_count'
        ]
    
    def get_products_count(self, obj):
        # Try cache first
        cache_key = f'cat:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.get_all_products_count()
            cache.set(cache_key, count, 3600)
        return count

class SubcategorySerializer(serializers.ModelSerializer):
    """Serializer for subcategories"""
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'image', 'icon', 'products_count']
    
    def get_products_count(self, obj):
        cache_key = f'cat:sub:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.products.filter(is_available=True).count()
            cache.set(cache_key, count, 3600)
        return count

class CategoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested subcategories"""
    subcategories = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    parent_category_name = serializers.CharField(source='parent_category.name', read_only=True)
    parent_name = serializers.CharField(source='parent.title', read_only=True)
    
    class Meta:
        model = Category
        fields = '__all__'
    
    def get_subcategories(self, obj):
        cache_key = f'cat:subs:{obj.slug}'
        subs = cache.get(cache_key)
        if subs is None:
            subs = obj.subcategories.filter(is_active=True)
            cache.set(cache_key, subs, 1800)
        return SubcategorySerializer(subs, many=True).data
    
    def get_products_count(self, obj):
        cache_key = f'cat:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.get_all_products_count()
            cache.set(cache_key, count, 3600)
        return count

# ========== TAG SERIALIZER ==========
class TagSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'products_count']
    
    def get_products_count(self, obj):
        cache_key = f'tag:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.products.filter(is_available=True).count()
            cache.set(cache_key, count, 3600)
        return count

# ========== BRAND SERIALIZER ==========
class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'is_active', 'products_count']
    
    def get_products_count(self, obj):
        cache_key = f'brand:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.products.filter(is_available=True).count()
            cache.set(cache_key, count, 3600)
        return count

# ========== PRODUCT REVIEW SERIALIZER ==========
class ProductReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.user.username', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = ['id', 'rating', 'title', 'comment', 'username', 'created', 'helpful_count']
        read_only_fields = ['user', 'created', 'helpful_count']

# ========== PRODUCT SERIALIZERS ==========
class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    category_name = serializers.CharField(source='category.title', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'short_description', 'price', 'discount_price',
            'discount_percentage', 'final_price', 'category_name', 'brand_name',
            'main', 'rating', 'review_count', 'is_available', 'in_stock',
            'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival',
            'condition', 'color', 'created'
        ]
        read_only_fields = fields

class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer with related data"""
    category = CategoryListSerializer(read_only=True)
    brand = serializers.CharField(source='brand.name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    available_sizes = ProductSizeSerializer(many=True, read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    seller_name = serializers.CharField(source='seller.user.username', read_only=True)
    related_products = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['created', 'updated', 'product_id']
    
    def get_reviews(self, obj):
        cache_key = f'prod:reviews:{obj.id}'
        reviews = cache.get(cache_key)
        if reviews is None:
            reviews = obj.reviews.select_related('user__user').order_by('-created')[:10]
            cache.set(cache_key, reviews, 1800)
        return ProductReviewSerializer(reviews, many=True).data
    
    def get_related_products(self, obj):
        cache_key = f'prod:related:{obj.id}'
        products = cache.get(cache_key)
        if products is None:
            products = list(
                Product.objects.filter(category=obj.category, is_available=True)
                .exclude(id=obj.id)
                .select_related('brand')[:6]
            )
            cache.set(cache_key, products, 1800)
        return ProductListSerializer(products, many=True).data

# ========== DEALS SERIALIZER ==========
class DealSerializer(CompactProductSerializer):
    """Special serializer for deals with discount emphasis"""
    class Meta:
        model = Product
        fields = CompactProductSerializer.Meta.fields + ['is_deal']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('dp') and data['dp'] > 0:
            data['badge'] = f"{data['dp']}% OFF"
        return data

# ========== TOP 100 GIFTS SERIALIZER ==========
class Top100GiftsSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Top100Gifts
        fields = ['id', 'title', 'description', 'is_active', 'products', 'products_count']
    
    def get_products(self, obj):
        cache_key = f'top100:{obj.id}'
        products = cache.get(cache_key)
        if products is None:
            products = obj.products.filter(is_available=True, in_stock__gt=0)[:20]
            cache.set(cache_key, products, 1800)
        return ProductListSerializer(products, many=True).data
    
    def get_products_count(self, obj):
        cache_key = f'top100:count:{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.products.count()
            cache.set(cache_key, count, 3600)
        return count

# ========== WISHLIST SERIALIZER ==========
class WishlistSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = ['id', 'products', 'products_count', 'created', 'updated']
    
    def get_products_count(self, obj):
        return obj.products.count()

# ========== CART PRODUCT SERIALIZER ==========
class CartProductSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_available=True),
        source='product',
        write_only=True
    )
    selected_size = ProductSizeSerializer(read_only=True)
    
    class Meta:
        model = CartProduct
        fields = ['id', 'product', 'product_id', 'quantity', 'selected_size', 'subtotal', 'created']
        read_only_fields = ['cart', 'subtotal']

# ========== CART SERIALIZER ==========
class CartSerializer(serializers.ModelSerializer):
    items = CartProductSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'profile', 'total', 'items', 'items_count', 'created', 'updated']
    
    def get_items_count(self, obj):
        return obj.items.count()

# ========== ORDER ITEM SERIALIZER ==========
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_price', 'quantity', 'selected_size', 'subtotal']

# ========== ORDER SERIALIZERS ==========
class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight order serializer for lists"""
    items_count = serializers.SerializerMethodField()
    order_status_display = serializers.CharField(source='get_order_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'order_by', 'amount', 'order_status',
            'order_status_display', 'payment_complete', 'payment_method', 
            'items_count', 'created'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()

class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order serializer with items"""
    items = OrderItemSerializer(many=True, read_only=True)
    order_status_display = serializers.CharField(source='get_order_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['order_number', 'ref', 'created', 'updated']

# ========== CHECKOUT SERIALIZER ==========
class CheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        exclude = ['cart', 'amount', 'order_status', 'subtotal', 'payment_complete', 'ref', 'order_number', 'user']

# ========== HOMEPAGE DATA SERIALIZER ==========
class HomepageDataSerializer(serializers.Serializer):
    """Optimized homepage data serializer"""
    hero_banner = serializers.DictField()
    featured_interests = CompactCategorySerializer(many=True)
    categories = CompactCategorySerializer(many=True)
    todays_deals = DealSerializer(many=True)
    editors_picks = CompactProductSerializer(many=True)
    new_arrivals = CompactProductSerializer(many=True)
    top100_gifts = CompactProductSerializer(many=True)

# ========== GIFT GUIDE SERIALIZERS ==========
class GiftGuideProductSerializer(serializers.ModelSerializer):
    product = CompactProductSerializer(read_only=True)
    
    class Meta:
        model = GiftGuideProduct
        fields = ['id', 'product', 'etsy_pick', 'custom_title', 'shop_name', 'badge_text', 'display_order']

class GiftGuideSectionSerializer(serializers.ModelSerializer):
    gift_products = serializers.SerializerMethodField()
    section_type_display = serializers.CharField(source='get_section_type_display', read_only=True)
    
    class Meta:
        model = GiftGuideSection
        fields = ['id', 'title', 'section_type', 'section_type_display', 'description', 'image', 'guide_links', 'gift_products']
    
    def get_gift_products(self, obj):
        cache_key = f'gift:section:{obj.id}'
        products = cache.get(cache_key)
        if products is None:
            products = obj.gift_products.select_related('product').order_by('display_order')[:10]
            cache.set(cache_key, products, 1800)
        return GiftGuideProductSerializer(products, many=True).data

# ========== GIFT FINDER SERIALIZERS ==========
class GiftOccasionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftOccasion
        fields = ['id', 'label', 'date', 'icon', 'slug', 'order']

class GiftPersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftPersona
        fields = ['id', 'name', 'persona_type', 'bg_color', 'accent_color', 'slug', 'order']

class GiftCollectionSerializer(serializers.ModelSerializer):
    persona = GiftPersonaSerializer(read_only=True)
    products = serializers.SerializerMethodField()
    
    class Meta:
        model = GiftCollection
        fields = ['id', 'persona', 'title', 'slug', 'description', 'interest_tag', 'products']
    
    def get_products(self, obj):
        cache_key = f'collection:{obj.id}:products'
        products = cache.get(cache_key)
        if products is None:
            collection_products = obj.collection_products.select_related('product').order_by('display_order')[:6]
            products = [cp.product for cp in collection_products if cp.product.is_available]
            cache.set(cache_key, products, 1800)
        return CompactProductSerializer(products, many=True).data
    
# Add these after your existing GiftCollectionSerializer

# ========== GIFT RECIPIENT SERIALIZERS ==========
class GiftRecipientItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftRecipientItem
        fields = ['id', 'title', 'image', 'slug', 'order']

class GiftRecipientSerializer(serializers.ModelSerializer):
    items = GiftRecipientItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = GiftRecipient
        fields = ['id', 'label', 'icon', 'slug', 'order', 'items']

# ========== GIFT INTEREST SERIALIZER ==========
class GiftInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftInterest
        fields = ['id', 'name', 'slug', 'order']

# ========== GIFT GRID ITEM SERIALIZER ==========
class GiftGridItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftGridItem
        fields = ['id', 'title', 'image', 'size', 'slug', 'order']

# ========== POPULAR GIFT CATEGORY SERIALIZER ==========
class PopularGiftCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PopularGiftCategory
        fields = ['id', 'name', 'slug', 'order']

# ========== GIFT TEASER SERIALIZERS ==========
class GiftTeaserFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftTeaserFeature
        fields = ['id', 'icon', 'text', 'order']

class GiftTeaserBannerSerializer(serializers.ModelSerializer):
    features = GiftTeaserFeatureSerializer(many=True, read_only=True)
    
    class Meta:
        model = GiftTeaserBanner
        fields = '__all__'

class GiftCardBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardBanner
        fields = '__all__'

class AboutGiftFinderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutGiftFinder
        fields = '__all__'

# ========== FASHION FINDS SERIALIZERS ==========
class FashionShopSerializer(serializers.ModelSerializer):
    featured_products_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = FashionShop
        fields = ['id', 'name', 'slug', 'rating', 'review_count', 'display_name', 
                  'description', 'logo', 'cover_image', 'featured_products_preview', 'order']
    
    def get_featured_products_preview(self, obj):
        products = obj.featured_products.filter(is_available=True, in_stock__gt=0)[:4]
        return CompactProductSerializer(products, many=True).data

class FashionPromoCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FashionPromoCard
        fields = '__all__'

class FashionTrendingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FashionTrending
        fields = '__all__'

class FashionDiscoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = FashionDiscover
        fields = '__all__'

# ========== HOMEPAGE SECTION SERIALIZER ==========
class HomepageSectionSerializer(serializers.ModelSerializer):
    products = CompactProductSerializer(many=True, read_only=True)
    categories = CompactCategorySerializer(many=True, read_only=True)
    section_type_display = serializers.CharField(source='get_section_type_display', read_only=True)
    
    class Meta:
        model = HomepageSection
        fields = ['id', 'title', 'section_type', 'section_type_display', 'description', 
                  'image', 'products', 'categories', 'order', 'is_active']