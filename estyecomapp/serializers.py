from rest_framework import serializers
from .models import *

#::::: PARENT CATEGORY SERIALIZER :::::
class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentCategory
        fields = '__all__'

#::::: CATEGORY SERIALIZER :::::
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
        return obj.products.filter(is_available=True).count()

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
    
    class Meta:
        model = Category
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

#::::: TAG SERIALIZER :::::
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

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

#::::: PRODUCT SERIALIZER :::::
class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    category_name = serializers.CharField(source='category.title', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'price', 'discount_price', 'discount_percentage',
            'final_price', 'category_name', 'brand_name', 'main', 'rating', 
            'review_count', 'is_available', 'is_featured', 'is_bestseller', 
            'is_deal', 'in_stock', 'condition', 'created'
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer with related data"""
    category = CategoryListSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    final_price = serializers.ReadOnlyField()
    seller_name = serializers.CharField(source='seller.user.username', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

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

#::::: ORDER SERIALIZER :::::
class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight order serializer for lists"""
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'order_by', 'amount', 'order_status',
            'payment_complete', 'payment_method', 'items_count', 'created'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()

class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order serializer with items"""
    items = OrderItemSerializer(many=True, read_only=True)
    
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
    
    class Meta:
        model = HomepageSection
        fields = '__all__'

#::::: NAVIGATION SERIALIZER :::::
class NavigationSerializer(serializers.Serializer):
    """Custom serializer for complex navigation structure"""
    parent_categories = ParentCategorySerializer(many=True)
    gift_occasions = CategoryListSerializer(many=True)
    gift_interests = CategoryListSerializer(many=True)
    gift_recipients = CategoryListSerializer(many=True)
    gift_popular = CategoryListSerializer(many=True)