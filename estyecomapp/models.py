from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q
import uuid
import secrets
import random
from .paystack import Paystack
from users.models import Profile

#::::: CATEGORY TYPES :::::
CATEGORY_TYPES = (
    ('main', 'Main Category'),
    ('gift_occasion', 'Gift Occasion'),
    ('gift_interest', 'Gift Interest'),
    ('gift_recipient', 'Gift For Everyone'),
    ('gift_popular', 'Popular Gifts'),
    ('homepage_section', 'Homepage Section'),
    ('gifts', 'Gifts'),
    ('fashion_finds', 'Fashion Finds'),
    ('home_favourites', 'Home Favourites'),
    ('special_collection', 'Special Collection'),
)

#::::: PARENT CATEGORY Model :::::
class ParentCategory(models.Model):
    """Top-level navigation categories like 'Gifts', 'Home & Living', etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='parent_categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Parent Categories'
    
    def __str__(self):
        return self.name
    
    def get_product_count(self):
        """Get total products across all categories"""
        count = 0
        for category in self.categories.filter(is_active=True):
            count += category.get_all_products_count()
        return count

#::::: CATEGORY Model :::::
class Category(models.Model):
    """Main product categories and subcategories"""
    parent_category = models.ForeignKey(
        ParentCategory, 
        on_delete=models.CASCADE, 
        related_name='categories',
        null=True,
        blank=True
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        related_name='subcategories',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    category_type = models.CharField(
        max_length=50, 
        choices=CATEGORY_TYPES, 
        default='main'
    )
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/')
    icon = models.CharField(max_length=50, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    show_in_top_100 = models.BooleanField(default=False)  # For Top 100 Gifts
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.title
    
    def get_all_products(self):
        """Get all products including from subcategories"""
        products = list(self.products.filter(is_available=True))
        for subcategory in self.subcategories.filter(is_active=True):
            products.extend(subcategory.get_all_products())
        return products
    
    def get_all_products_count(self):
        """Get count of all products including subcategories"""
        count = self.products.filter(is_available=True).count()
        for subcategory in self.subcategories.filter(is_active=True):
            count += subcategory.get_all_products_count()
        return count
    
    def get_top_rated_products(self, limit=10):
        """Get top rated products from this category"""
        return self.products.filter(
            is_available=True,
            rating__gte=4.0
        ).order_by('-rating', '-review_count')[:limit]

#::::: PRODUCT TAGS Model :::::
class Tag(models.Model):
    """Tags for better product organization and search"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

#::::: BRAND Model :::::
class Brand(models.Model):
    """Product brands/manufacturers"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

#::::: PRODUCT SIZE Model :::::
class ProductSize(models.Model):
    """Size options for products"""
    SIZE_CATEGORIES = (
        ('clothing', 'Clothing'),
        ('shoes', 'Shoes'),
        ('jewelry', 'Jewelry'),
        ('home', 'Home & Living'),
        ('other', 'Other'),
    )
    
    category = models.CharField(max_length=50, choices=SIZE_CATEGORIES)
    name = models.CharField(max_length=50)  # e.g., 'Small', 'Medium', 'Large', '8', '9', '10'
    code = models.CharField(max_length=20)  # e.g., 'S', 'M', 'L', '8', '9', '10'
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['category', 'code']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"

#::::: PRODUCT Model :::::
class Product(models.Model):
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('good', 'Good'),
        ('vintage', 'Vintage'),
        ('handmade', 'Handmade'),
    )
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')
    available_sizes = models.ManyToManyField(ProductSize, blank=True, related_name='products')
    
    # Images
    main = models.ImageField(upload_to='products/')
    photo1 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo2 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo3 = models.ImageField(upload_to='products/', null=True, blank=True)
    photo4 = models.ImageField(upload_to='products/', null=True, blank=True)
    
    # Product details
    product_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    
    # Inventory
    is_available = models.BooleanField(default=True)
    in_stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    out_of_stock_date = models.DateField(null=True, blank=True)
    restock_date = models.DateField(null=True, blank=True)
    
    # Features
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_deal = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    include_in_top_100 = models.BooleanField(default=False)  # For Top 100 Gifts selection
    
    # Physical attributes (optional)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Weight in kg")
    dimensions = models.CharField(max_length=100, blank=True, null=True, help_text="L x W x H in cm")
    color = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    
    # Ratings and reviews
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(default=0)
    
    # SEO and metadata
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Seller information
    seller = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='products_sold',
        null=True,
        blank=True
    )
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['is_featured', 'is_deal']),
            models.Index(fields=['-created']),
            models.Index(fields=['-rating']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.product_id:
            self.product_id = uuid.uuid4()
        
        # Set out_of_stock_date when stock reaches 0
        if self.in_stock == 0 and not self.out_of_stock_date:
            from django.utils import timezone
            self.out_of_stock_date = timezone.now().date()
        elif self.in_stock > 0 and self.out_of_stock_date:
            self.out_of_stock_date = None
        
        super().save(*args, **kwargs)
    
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
        """Return star rating as tuple (full_stars, half_star, empty_stars)"""
        full_stars = int(self.rating)
        has_half = (self.rating - full_stars) >= 0.5
        half_star = 1 if has_half else 0
        empty_stars = 5 - full_stars - half_star
        return (full_stars, half_star, empty_stars)

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