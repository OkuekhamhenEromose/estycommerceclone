from rest_framework import serializers
from .models import *

#::::: PRODUCT SIZE SERIALIZER :::::
class ProductSizeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = ProductSize
        fields = '__all__'

#::::: PARENT CATEGORY SERIALIZER :::::
class ParentCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentCategory
        fields = '__all__'
    
    def get_product_count(self, obj):
        return obj.get_product_count()

#::::: CATEGORY SERIALIZERS :::::
class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for category lists"""
    subcategories_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'title', 'slug', 'category_type', 'image', 
            'icon', 'order', 'is_active', 'is_featured',
            'subcategories_count', 'products_count'
        ]
    
    def get_subcategories_count(self, obj):
        return obj.subcategories.filter(is_active=True).count()
    
    def get_products_count(self, obj):
        return obj.get_all_products_count()

class SubcategorySerializer(serializers.ModelSerializer):
    """Serializer for subcategories"""
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'image', 'icon', 'products_count']
    
    def get_products_count(self, obj):
        return obj.products.filter(is_available=True).count()

class CategoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested subcategories"""
    subcategories = SubcategorySerializer(many=True, read_only=True)
    parent_category_name = serializers.CharField(source='parent_category.name', read_only=True)
    parent_name = serializers.CharField(source='parent.title', read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = '__all__'
    
    def get_products_count(self, obj):
        return obj.get_all_products_count()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

#::::: TAG SERIALIZER :::::
class TagSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = '__all__'
    
    def get_products_count(self, obj):
        return obj.products.filter(is_available=True).count()

#::::: BRAND SERIALIZER :::::
class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = '__all__'
    
    def get_products_count(self, obj):
        return obj.products.filter(is_available=True).count()

#::::: PRODUCT REVIEW SERIALIZER :::::
class ProductReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.user.username', read_only=True)
    user_image = serializers.ImageField(source='user.image', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = '__all__'
        read_only_fields = ['user', 'created', 'updated', 'helpful_count']

#::::: PRODUCT SERIALIZERS :::::
class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    category_name = serializers.CharField(source='category.title', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()
    star_rating = serializers.SerializerMethodField()
    available_sizes = ProductSizeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'short_description', 'price', 'discount_price', 
            'discount_percentage', 'final_price', 'category_name', 'brand_name', 
            'main', 'rating', 'review_count', 'star_rating', 'is_available', 
            'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival',
            'in_stock', 'is_low_stock', 'is_out_of_stock', 'condition', 
            'available_sizes', 'color', 'created'
        ]
    
    def get_star_rating(self, obj):
        full, half, empty = obj.get_star_rating_display()
        return {
            'full_stars': full,
            'half_star': half,
            'empty_stars': empty,
            'rating_value': float(obj.rating)
        }

class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer with related data"""
    category = CategoryListSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    available_sizes = ProductSizeSerializer(many=True, read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()
    star_rating = serializers.SerializerMethodField()
    seller_name = serializers.CharField(source='seller.user.username', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def get_star_rating(self, obj):
        full, half, empty = obj.get_star_rating_display()
        return {
            'full_stars': full,
            'half_star': half,
            'empty_stars': empty,
            'rating_value': float(obj.rating)
        }

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

#::::: TOP 100 GIFTS SERIALIZER :::::
class Top100GiftsSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Top100Gifts
        fields = '__all__'
    
    def get_products_count(self, obj):
        return obj.products.count()

class Top100GiftsRandomSerializer(serializers.ModelSerializer):
    """Serializer with random selection of products"""
    random_products = serializers.SerializerMethodField()
    
    class Meta:
        model = Top100Gifts
        fields = ['id', 'title', 'description', 'is_active', 'random_products']
    
    def get_random_products(self, obj):
        count = self.context.get('random_count', 20)
        products = obj.get_random_selection(count)
        return ProductListSerializer(products, many=True).data

#::::: WISHLIST SERIALIZER :::::
class WishlistSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = '__all__'
    
    def get_products_count(self, obj):
        return obj.products.count()

#::::: CART PRODUCT SERIALIZER :::::
class CartProductSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    selected_size = ProductSizeSerializer(read_only=True)
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductSize.objects.all(),
        source='selected_size',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = CartProduct
        fields = '__all__'
        read_only_fields = ['cart', 'subtotal']

#::::: CART SERIALIZER :::::
class CartSerializer(serializers.ModelSerializer):
    items = CartProductSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = '__all__'
    
    def get_items_count(self, obj):
        return obj.items.count()

#::::: ORDER ITEM SERIALIZER :::::
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

#::::: ORDER SERIALIZERS :::::
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
        read_only_fields = [
            'order_number', 'ref', 'created', 'updated',
            'payment_complete', 'order_status'
        ]

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

#::::: CHECKOUT SERIALIZER :::::
class CheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        exclude = [
            'cart', 'amount', 'order_status', 'subtotal', 
            'payment_complete', 'ref', 'order_number', 'user'
        ]

#::::: HOMEPAGE SECTION SERIALIZER :::::
class HomepageSectionSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    categories = CategoryListSerializer(many=True, read_only=True)
    section_type_display = serializers.CharField(source='get_section_type_display', read_only=True)
    
    class Meta:
        model = HomepageSection
        fields = '__all__'

#::::: CATEGORY GROUP SERIALIZER :::::
class CategoryGroupSerializer(serializers.Serializer):
    """Serializer for grouped categories with products"""
    category = CategoryDetailSerializer()
    featured_products = ProductListSerializer(many=True)
    top_rated_products = ProductListSerializer(many=True)
    product_count = serializers.IntegerField()

#::::: NAVIGATION SERIALIZER :::::
class NavigationSerializer(serializers.Serializer):
    """Custom serializer for complex navigation structure"""
    parent_categories = ParentCategorySerializer(many=True)
    gift_occasions = CategoryListSerializer(many=True)
    gift_interests = CategoryListSerializer(many=True)
    gift_recipients = CategoryListSerializer(many=True)
    gift_popular = CategoryListSerializer(many=True)
    gifts_section = CategoryListSerializer(many=True)
    fashion_finds = CategoryListSerializer(many=True)
    home_favourites = CategoryListSerializer(many=True)