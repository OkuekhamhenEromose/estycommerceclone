from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
import uuid
import secrets
import random
from users.models import Profile
from django.db.models import Q

# ========== CACHE KEYS ==========
class CacheKeys:
    """Centralized cache key management"""
    CATEGORY_PREFIX = 'cat:'
    PRODUCT_PREFIX = 'prod:'
    HOMEPAGE = 'homepage:data'
    DEALS = 'deals:list'
    GIFT_GUIDES = 'gift:guides'
    TOP_100 = 'top:100'
    COLLECTION_PREFIX = 'coll:'
    
    @staticmethod
    def category(slug): return f"{CacheKeys.CATEGORY_PREFIX}{slug}"
    @staticmethod
    def product(slug): return f"{CacheKeys.PRODUCT_PREFIX}{slug}"
    @staticmethod
    def category_products(slug, limit=20): return f"cat:prod:{slug}:{limit}"
    @staticmethod
    def collection(id): return f"{CacheKeys.COLLECTION_PREFIX}{id}"
    @staticmethod
    def parent_category(id): return f"parent:cat:{id}"

# ========== CATEGORY TYPES ==========
CATEGORY_TYPES = (
    ('main', 'Main Category'),
    ('gift_occasion', 'Gift Occasion'),
    ('gift_interest', 'Gift Interest'),
    ('gift_recipient', 'Gift For Everyone'),
    ('gift_popular', 'Popular Gifts'),
    ('gifts', 'Gifts'),
    ('fashion_finds', 'Fashion Finds'),
    ('home_favourites', 'Home Favourites'),
)

# ========== PARENT CATEGORY ==========
class ParentCategory(models.Model):
    """Top-level navigation categories with caching"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='parent_categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Parent Categories'
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['is_featured', 'order']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Clear homepage cache when categories change
        cache.delete(CacheKeys.HOMEPAGE)
        cache.delete(CacheKeys.parent_category(self.id))
    
    def delete(self, *args, **kwargs):
        cache.delete(CacheKeys.HOMEPAGE)
        cache.delete(CacheKeys.parent_category(self.id))
        super().delete(*args, **kwargs)
    
    def get_product_count(self):
        """Cached product count"""
        cache_key = f'parent:cat:count:{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = sum(c.get_all_products_count() for c in self.categories.filter(is_active=True))
            cache.set(cache_key, count, 3600)  # 1 hour
        return count

# ========== CATEGORY ==========
class Category(models.Model):
    """Main product categories with caching"""
    parent_category = models.ForeignKey(
        ParentCategory, on_delete=models.CASCADE, related_name='categories',
        null=True, blank=True, db_index=True
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name='subcategories',
        null=True, blank=True, db_index=True
    )
    title = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    category_type = models.CharField(
        max_length=50, choices=CATEGORY_TYPES, default='main', db_index=True
    )
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/')
    icon = models.CharField(max_length=50, blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    show_in_top_100 = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['category_type', 'is_featured']),
            models.Index(fields=['parent', 'order']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        # Clear related caches
        cache.delete(CacheKeys.category(self.slug))
        cache.delete(CacheKeys.HOMEPAGE)
        if self.parent_category_id:
            cache.delete(CacheKeys.parent_category(self.parent_category_id))
    
    def delete(self, *args, **kwargs):
        cache.delete(CacheKeys.category(self.slug))
        cache.delete(CacheKeys.HOMEPAGE)
        if self.parent_category_id:
            cache.delete(CacheKeys.parent_category(self.parent_category_id))
        super().delete(*args, **kwargs)
    
    def get_all_products(self, limit=20):
        """Get products with caching"""
        cache_key = CacheKeys.category_products(self.slug, limit)
        products = cache.get(cache_key)
        if products is None:
            products = list(
                self.products.filter(is_available=True, in_stock__gt=0)
                .select_related('brand')
                .only('id', 'title', 'slug', 'price', 'discount_price', 
                     'main', 'rating', 'review_count', 'brand__name')
                .order_by('-rating')[:limit]
            )
            cache.set(cache_key, products, 1800)  # 30 minutes
        return products
    
    def get_all_products_count(self):
        """Cached count"""
        cache_key = f'cat:count:{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = self.products.filter(is_available=True).count()
            for sub in self.subcategories.filter(is_active=True):
                count += sub.get_all_products_count()
            cache.set(cache_key, count, 3600)  # 1 hour
        return count
    
    def get_top_rated_products(self, limit=10):
        """Get top rated products with caching"""
        cache_key = f'cat:top:{self.slug}:{limit}'
        products = cache.get(cache_key)
        if products is None:
            products = list(
                self.products.filter(is_available=True, rating__gte=4.0)
                .select_related('brand')
                .only('id', 'title', 'slug', 'price', 'discount_price', 
                     'main', 'rating', 'review_count')
                .order_by('-rating', '-review_count')[:limit]
            )
            cache.set(cache_key, products, 1800)  # 30 minutes
        return products

# ========== BRAND ==========
class Brand(models.Model):
    """Product brands with caching"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [models.Index(fields=['slug', 'is_active'])]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete_pattern('brand:*')
    
    def delete(self, *args, **kwargs):
        cache.delete_pattern('brand:*')
        super().delete(*args, **kwargs)

# ========== TAG ==========
class Tag(models.Model):
    """Product tags with caching"""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# ========== PRODUCT SIZE ==========
class ProductSize(models.Model):
    """Size options for products"""
    SIZE_CATEGORIES = (
        ('clothing', 'Clothing'),
        ('shoes', 'Shoes'),
        ('jewelry', 'Jewelry'),
        ('home', 'Home & Living'),
        ('other', 'Other'),
    )
    
    category = models.CharField(max_length=50, choices=SIZE_CATEGORIES, db_index=True)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['category', 'code']
        indexes = [models.Index(fields=['category', 'code'])]
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"

# ========== PRODUCT ==========
class Product(models.Model):
    """Main product model with extensive caching"""
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('good', 'Good'),
        ('vintage', 'Vintage'),
        ('handmade', 'Handmade'),
    )
    
    # Core fields
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    tags = models.ManyToManyField(Tag, blank=True)
    available_sizes = models.ManyToManyField(ProductSize, blank=True)
    
    # Images
    main = models.ImageField(upload_to='products/')
    photo1 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo2 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo3 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo4 = models.ImageField(upload_to='products/', null=True, blank=True)
    
    # Product details
    product_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    
    # Inventory
    is_available = models.BooleanField(default=True, db_index=True)
    in_stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    out_of_stock_date = models.DateField(null=True, blank=True)
    restock_date = models.DateField(null=True, blank=True)
    
    # Features
    is_featured = models.BooleanField(default=False, db_index=True)
    is_bestseller = models.BooleanField(default=False, db_index=True)
    is_deal = models.BooleanField(default=False, db_index=True)
    is_new_arrival = models.BooleanField(default=False, db_index=True)
    include_in_top_100 = models.BooleanField(default=False)
    
    # Physical attributes
    color = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    
    # Ratings
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(default=0)
    
    # SEO
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Seller
    seller = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='products_sold',
        null=True, blank=True, db_index=True
    )
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['is_featured', 'is_deal']),
            models.Index(fields=['-rating']),
            models.Index(fields=['is_deal', '-discount_price']),
            models.Index(fields=['is_bestseller', '-rating']),
            models.Index(fields=['is_new_arrival', '-created']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_slug = None
        if not is_new:
            try:
                old_slug = Product.objects.get(pk=self.pk).slug
            except Product.DoesNotExist:
                pass
        
        if not self.product_id:
            self.product_id = uuid.uuid4()
        
        # Set out_of_stock_date when stock reaches 0
        if self.in_stock == 0 and not self.out_of_stock_date:
            from django.utils import timezone
            self.out_of_stock_date = timezone.now().date()
        elif self.in_stock > 0 and self.out_of_stock_date:
            self.out_of_stock_date = None
        
        super().save(*args, **kwargs)
        
        # Clear caches
        cache.delete(CacheKeys.product(self.slug))
        if old_slug and old_slug != self.slug:
            cache.delete(CacheKeys.product(old_slug))
        cache.delete(CacheKeys.HOMEPAGE)
        cache.delete(CacheKeys.DEALS)
        cache.delete_pattern(f'cat:prod:{self.category.slug}:*')
    
    def delete(self, *args, **kwargs):
        cache.delete(CacheKeys.product(self.slug))
        cache.delete(CacheKeys.HOMEPAGE)
        cache.delete(CacheKeys.DEALS)
        cache.delete_pattern(f'cat:prod:{self.category.slug}:*')
        super().delete(*args, **kwargs)
    
    @property
    def discount_percentage(self):
        if self.discount_price and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0
    
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price
    
    @property
    def is_low_stock(self):
        return 0 < self.in_stock <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        return self.in_stock == 0
    
    def get_star_rating_display(self):
        full_stars = int(self.rating)
        has_half = (self.rating - full_stars) >= 0.5
        half_star = 1 if has_half else 0
        empty_stars = 5 - full_stars - half_star
        return (full_stars, half_star, empty_stars)

# ========== SIGNAL HANDLERS ==========
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    cache.delete(CacheKeys.category(instance.slug))
    cache.delete_pattern('cat:prod:*')

@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_product_caches(sender, instance, **kwargs):
    cache.delete(CacheKeys.DEALS)
    cache.delete(CacheKeys.HOMEPAGE)
    if instance.category:
        cache.delete_pattern(f'cat:prod:{instance.category.slug}:*')

#::::: TOP 100 GIFTS Model :::::
class Top100Gifts(models.Model):
    """Curated collection of top 100 gifts with random selection"""
    title = models.CharField(max_length=200, default="Top 100 Gifts")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    auto_populate = models.BooleanField(default=True, help_text="Automatically populate with best products")
    products = models.ManyToManyField(Product, blank=True, related_name='top_100_collections')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Top 100 Gifts Collection"
        verbose_name_plural = "Top 100 Gifts Collections"
    
    def __str__(self):
        return self.title
    
    def populate_products(self):
        """Automatically populate with top 100 best products based on rating, reviews, and sales"""
        if not self.auto_populate:
            return
        
        # Get products marked for Top 100 or highly rated products
        top_products = Product.objects.filter(
            Q(include_in_top_100=True) | Q(rating__gte=4.0),
            is_available=True,
            in_stock__gt=0
        ).order_by('-rating', '-review_count', '-is_bestseller')[:100]
        
        self.products.set(top_products)
    
    def get_random_selection(self, count=20):
        """Get random selection from top 100"""
        all_products = list(self.products.filter(is_available=True, in_stock__gt=0))
        if len(all_products) <= count:
            return all_products
        return random.sample(all_products, count)

#::::: PRODUCT REVIEW Model :::::
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f'{self.user.user.username} - {self.product.title} - {self.rating}★'

#::::: WISHLIST Model :::::
class Wishlist(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, blank=True, related_name='wishlisted_by')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.user.user.username}\'s Wishlist'

#::::: CART Model :::::
class Cart(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Cart {self.id} - ${self.total}'
    
    def update_total(self):
        """Recalculate cart total"""
        total = sum(item.subtotal for item in self.items.all())
        self.total = total
        self.save()

#::::: CART PRODUCT Model :::::
class CartProduct(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    selected_size = models.ForeignKey(ProductSize, on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product', 'selected_size']
    
    def __str__(self):
        size_info = f" ({self.selected_size.code})" if self.selected_size else ""
        return f'Cart {self.cart.id} - {self.product.title}{size_info} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.product.final_price * self.quantity
        super().save(*args, **kwargs)

#::::: ORDER STATUS AND PAYMENT METHODS :::::
ORDER_STATUS = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
)

PAYMENT_METHOD = (
    ('paystack', 'Paystack'),
    ('paypal', 'PayPal'),
    ('transfer', 'Bank Transfer'),
    ('cash', 'Cash on Delivery'),
)

#::::: ORDER Model :::::
class Order(models.Model):
    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    
    # Shipping information
    order_by = models.CharField(max_length=255, blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_state = models.CharField(max_length=100, blank=True, null=True)
    shipping_zipcode = models.CharField(max_length=20, blank=True, null=True)
    shipping_country = models.CharField(max_length=100, default='Nigeria', blank=True, null=True)
    mobile = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Order details
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status and payment
    order_status = models.CharField(max_length=50, choices=ORDER_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD, default='paystack')
    payment_complete = models.BooleanField(default=False)
    ref = models.CharField(max_length=255, null=True, blank=True, unique=True)
    
    # Notes
    order_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f'Order {self.order_number} - ${self.amount}'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f'ORD-{uuid.uuid4().hex[:10].upper()}'
        
        if not self.ref:
            ref = secrets.token_urlsafe(50)
            while Order.objects.filter(ref=ref).exists():
                ref = secrets.token_urlsafe(50)
            self.ref = ref
        
        super().save(*args, **kwargs)
    
    def amount_value(self):
        """Convert amount to kobo for Paystack"""
        return int(self.amount * 100)

#::::: ORDER ITEM Model :::::
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    selected_size = models.CharField(max_length=50, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        size_info = f" ({self.selected_size})" if self.selected_size else ""
        return f'{self.product_name}{size_info} x {self.quantity}'

#::::: HOMEPAGE SECTION Model :::::
class HomepageSection(models.Model):
    SECTION_TYPES = (
        ('picks_inspired', 'Picks Inspired by Shopping'),
        ('featured_interests', 'Featured Interests'),
        ('seasonal', 'Special Season'),
        ('big_deals', 'Today\'s Big Deals'),
        ('editors_guide', 'Editor\'s Guide'),
        ('vintage_guide', 'Vintage Guide'),
        ('banner', 'Banner'),
        ('gifts', 'Gifts Section'),
        ('top_100_gifts', 'Top 100 Gifts'),
        ('fashion_finds', 'Fashion Finds'),
        ('home_favourites', 'Home Favourites'),
        ('gift_guides', 'Best Gift Guides'),
        ('valentines_gifts', 'Valentine\'s Day Gifts'),
        ('best_of_valentine', "Best of Valentine's Day"),
        ('bestselling_gifts', 'Best-Selling Gifts'),
        ('personalized_presents', 'Presents to Personalize'),
        ('fashion_trending', 'Fashion Trending Now'),
        ('fashion_promo', 'Fashion Promo Cards'),
        ('fashion_shops', 'Fashion Shops We Love'),
        ('fashion_discover', 'Fashion Discover More'),
    )
    
    title = models.CharField(max_length=200)
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='homepage_sections/', blank=True, null=True)
    products = models.ManyToManyField(Product, blank=True, related_name='homepage_sections')
    categories = models.ManyToManyField(Category, blank=True, related_name='homepage_sections')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title

# Add new Gift Section models at the end of the file
class GiftGuideSection(models.Model):
    """Special sections for the gifts page"""
    SECTION_CHOICES = (
        ('best_gift_guides', 'Best Gift Guides'),
        ('valentines_gifts', 'Valentine\'s Day Gifts'),
        ('bestselling_gifts', 'Best-Selling Gifts'),
        ('best_of_valentine',"Best of Valentine's Day"),
        ('personalized_presents', 'Presents to Personalize'),
    )
    
    title = models.CharField(max_length=200)
    section_type = models.CharField(max_length=50, choices=SECTION_CHOICES)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='gift_sections/', blank=True, null=True)
    background_image = models.ImageField(upload_to='gift_sections/backgrounds/', blank=True, null=True)
    
    # Content for Best Gift Guides
    guide_links = models.JSONField(default=list, blank=True, null=True, 
        help_text="List of guide links in format: {'title': '...', 'url': '...'}")
    
    # Featured products for the section
    featured_products = models.ManyToManyField(Product, blank=True, related_name='gift_guide_sections')
    
    # Filter categories
    categories = models.ManyToManyField(Category, blank=True, related_name='gift_guide_sections')
    
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Gift Guide Section"
        verbose_name_plural = "Gift Guide Sections"
    
    def __str__(self):
        return f"{self.get_section_type_display()} - {self.title}"

class GiftGuideProduct(models.Model):
    """Featured products within gift guide sections with additional metadata"""
    gift_section = models.ForeignKey(GiftGuideSection, on_delete=models.CASCADE, related_name='gift_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gift_guide_entries')
    
    # Custom metadata for display
    etsy_pick = models.BooleanField(default=False, help_text="Marked as Etsy's Pick")
    custom_title = models.CharField(max_length=255, blank=True, null=True, help_text="Custom title for display")
    custom_description = models.TextField(blank=True, null=True, help_text="Custom description")
    display_order = models.PositiveIntegerField(default=0)
    
    # Additional display info
    shop_name = models.CharField(max_length=100, blank=True, null=True)
    badge_text = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., '25% off', 'Free delivery'")
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created']
        unique_together = ['gift_section', 'product']
    
    def __str__(self):
        return f"{self.gift_section.title} - {self.product.title}"
    
class FashionShop(models.Model):
    """Small shops for Fashion Finds section"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(default=0)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='fashion_shops/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='fashion_shops/covers/', blank=True, null=True)
    
    # Products to display for this shop
    featured_products = models.ManyToManyField(Product, blank=True, related_name='fashion_shops')
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

# Add a model for Fashion Promo Cards
class FashionPromoCard(models.Model):
    """Promotional cards for Fashion Finds"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='fashion_promo/')
    button_text = models.CharField(max_length=50, default="Shop now")
    button_url = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title

# Add a model for Fashion Trending
class FashionTrending(models.Model):
    """Trending section for Fashion Finds"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField()
    image = models.ImageField(upload_to='fashion_trending/')
    button_text = models.CharField(max_length=50, default="Try it out")
    button_url = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

# Add a model for Fashion Discover More
class FashionDiscover(models.Model):
    """Discover more section for Fashion Finds"""
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='fashion_discover/')
    url = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title

#::::: GIFT FINDER MODELS :::::

class GiftOccasion(models.Model):
    """Gift occasions for the gift finder hero section"""
    label = models.CharField(max_length=100)
    date = models.CharField(max_length=20, blank=True, null=True)
    icon = models.CharField(max_length=50)  # Lucide icon name
    slug = models.SlugField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'label']
    
    def __str__(self):
        return self.label

class GiftPersona(models.Model):
    """Personas for gift ideas (e.g., The Vegetarian, The Jewellery Lover)"""
    PERSONA_TYPES = (
        ('collection', 'Collection Persona'),
        ('guilty_pleasure', 'Guilty Pleasure'),
        ('zodiac_sign', 'Zodiac Sign'),
        ('interest', 'Interest'),
        ('related_idea', 'Related Gift Idea'),
    )
    
    name = models.CharField(max_length=100)
    persona_type = models.CharField(max_length=50, choices=PERSONA_TYPES, default='collection')
    title = models.CharField(max_length=200, blank=True, null=True)  # For collection titles
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='gift_personas/', blank=True, null=True)
    bg_color = models.CharField(max_length=50, blank=True, null=True)  # Tailwind class
    accent_color = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.get_persona_type_display()} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class GiftCollection(models.Model):
    """Gift collections featured in Browse by Interest"""
    persona = models.ForeignKey(GiftPersona, on_delete=models.CASCADE, related_name='collections')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    interest_tag = models.CharField(max_length=100, blank=True, null=True)  # For filtering by interest
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return f"{self.persona.name} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.persona.name}-{self.title}")
        super().save(*args, **kwargs)

class GiftCollectionProduct(models.Model):
    """Products in gift collections"""
    collection = models.ForeignKey(GiftCollection, on_delete=models.CASCADE, related_name='collection_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gift_collections')
    custom_title = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created']
        unique_together = ['collection', 'product']
    
    def __str__(self):
        return f"{self.collection.title} - {self.product.title}"

class GiftRecipient(models.Model):
    """Recipient categories for Extraordinary Finds section"""
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)  # Lucide icon name
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'label']
    
    def __str__(self):
        return self.label
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)
        super().save(*args, **kwargs)

class GiftRecipientItem(models.Model):
    """Items within recipient categories"""
    recipient = models.ForeignKey(GiftRecipient, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gift_recipients/', blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipient_items')
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return f"{self.recipient.label} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.recipient.label}-{self.title}")
        super().save(*args, **kwargs)

class GiftGridItem(models.Model):
    """Items for the gift grid on hero section"""
    SIZE_CHOICES = (
        ('small', 'Small'),
        ('large', 'Large'),
    )
    
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gift_grid/')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='small')
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='gift_grid_items')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class GiftInterest(models.Model):
    """Interests for the Browse by Interest section"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class PopularGiftCategory(models.Model):
    """Categories for Discover Popular Gifts section"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

#::::: GIFT TEASER MODELS :::::

class GiftTeaserBanner(models.Model):
    """Gift teaser banner content"""
    title = models.CharField(max_length=200)
    badge_text = models.CharField(max_length=50, default="✨ New")
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created']
    
    def __str__(self):
        return self.title

class GiftTeaserFeature(models.Model):
    """Features list for gift teaser"""
    banner = models.ForeignKey(GiftTeaserBanner, on_delete=models.CASCADE, related_name='features')
    icon = models.CharField(max_length=50)  # Lucide icon name
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.banner.title} - {self.text[:30]}"

class GiftCardBanner(models.Model):
    """Gift card banner content"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    button_text = models.CharField(max_length=50, default="Pick a design")
    button_url = models.CharField(max_length=500, default="/gift-cards")
    gradient_from = models.CharField(max_length=50, default="from-yellow-300")
    gradient_via = models.CharField(max_length=50, default="via-orange-400")
    gradient_to = models.CharField(max_length=50, default="to-green-500")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created']
    
    def __str__(self):
        return self.title

class AboutGiftFinder(models.Model):
    """About section content for Gift Finder"""
    title = models.CharField(max_length=200, default="If you need gift ideas for anybody – and we mean ANYBODY – in your life, you've come to the right place.")
    description = models.TextField()
    icon = models.CharField(max_length=50, default="Gift")
    button_text_more = models.CharField(max_length=20, default="More")
    button_text_less = models.CharField(max_length=20, default="Less")
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return "About Gift Finder"