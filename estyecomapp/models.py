from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import secrets
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
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Parent Categories'
    
    def __str__(self):
        return self.name

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
    icon = models.CharField(max_length=50, blank=True, null=True)  # For icon classes
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.title
    
    def get_all_products(self):
        """Get all products including from subcategories"""
        products = list(self.products.all())
        for subcategory in self.subcategories.all():
            products.extend(subcategory.get_all_products())
        return products

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
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')
    
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
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_deal = models.BooleanField(default=False)
    in_stock = models.PositiveIntegerField(default=0)
    
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
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.product_id:
            self.product_id = uuid.uuid4()
        super().save(*args, **kwargs)
    
    @property
    def discount_percentage(self):
        if self.discount_price and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0
    
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price

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
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f'Cart {self.cart.id} - {self.product.title} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.product.final_price * self.quantity
        super().save(*args, **kwargs)

#::::: ORDER Model :::::
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
    # Make order_number nullable temporarily
    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    
    # Shipping information
    order_by = models.CharField(max_length=255, blank=True, null=True)# "blank=True, null=True" means optional
    shipping_address = models.TextField(blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_state = models.CharField(max_length=100, blank=True, null=True)
    shipping_zipcode = models.CharField(max_length=20, blank=True, null=True)
    shipping_country = models.CharField(max_length=100, default='Nigeria', blank=True, null=True)
    mobile = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Order details with defaults
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
            # Ensure unique ref
            while Order.objects.filter(ref=ref).exists():
                ref = secrets.token_urlsafe(50)
            self.ref = ref
        
        super().save(*args, **kwargs)


#::::: ORDER ITEM Model :::::
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return f'{self.product_name} x {self.quantity}'

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