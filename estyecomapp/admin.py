from django.contrib import admin
from .models import *

#::::: PARENT CATEGORY ADMIN :::::
@admin.register(ParentCategory)
class ParentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

#::::: CATEGORY ADMIN :::::
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'category_type', 'parent', 'parent_category', 'order', 'is_active', 'is_featured']
    list_filter = ['category_type', 'is_active', 'is_featured', 'parent_category', 'created']
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['order', 'title']
    list_per_page = 50

#::::: TAG ADMIN :::::
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

#::::: BRAND ADMIN :::::
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

#::::: PRODUCT ADMIN :::::
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'slug', 'category', 'brand', 'price', 
        'discount_price', 'condition', 'in_stock', 'rating', 
        'is_available', 'is_featured', 'is_bestseller', 'is_deal', 'created'
    ]
    list_filter = [
        'category', 'brand', 'condition', 'is_available', 
        'is_featured', 'is_bestseller', 'is_deal', 'created'
    ]
    search_fields = ['title', 'slug', 'description', 'sku']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags']
    readonly_fields = ['product_id', 'created', 'updated']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'category', 'brand', 'tags', 'seller')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Images', {
            'fields': ('main', 'photo1', 'photo2', 'photo3', 'photo4')
        }),
        ('Inventory', {
            'fields': ('sku', 'in_stock', 'condition')
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'is_bestseller', 'is_deal')
        }),
        ('Ratings', {
            'fields': ('rating', 'review_count')
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('product_id', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 50

#::::: PRODUCT REVIEW ADMIN :::::
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'helpful_count', 'created']
    list_filter = ['rating', 'is_verified_purchase', 'created']
    search_fields = ['product__title', 'user__user__username', 'comment']
    readonly_fields = ['created', 'updated']
    list_per_page = 50

#::::: WISHLIST ADMIN :::::
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_products_count', 'created', 'updated']
    search_fields = ['user__user__username']
    filter_horizontal = ['products']
    readonly_fields = ['created', 'updated']
    
    def get_products_count(self, obj):
        return obj.products.count()
    get_products_count.short_description = 'Products Count'

#::::: CART PRODUCT INLINE :::::
class CartProductInline(admin.TabularInline):
    model = CartProduct
    extra = 0
    readonly_fields = ['subtotal', 'created', 'updated']
    fields = ['product', 'quantity', 'subtotal']

#::::: CART ADMIN :::::
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'total', 'get_items_count', 'created', 'updated']
    list_filter = ['created', 'updated']
    search_fields = ['profile__user__username', 'session_key']
    readonly_fields = ['total', 'created', 'updated']
    inlines = [CartProductInline]
    
    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Items Count'

#::::: CART PRODUCT ADMIN :::::
@admin.register(CartProduct)
class CartProductAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'subtotal', 'created']
    list_filter = ['created']
    search_fields = ['cart__id', 'product__title']
    readonly_fields = ['subtotal', 'created', 'updated']

#::::: ORDER ITEM INLINE :::::
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'quantity', 'subtotal']
    fields = ['product', 'product_name', 'product_price', 'quantity', 'subtotal']

#::::: ORDER ADMIN :::::
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'order_by', 'amount', 
        'order_status', 'payment_method', 'payment_complete', 'created'
    ]
    list_filter = [
        'order_status', 'payment_method', 'payment_complete', 
        'shipping_country', 'created'
    ]
    search_fields = [
        'order_number', 'ref', 'order_by', 'email', 
        'mobile', 'user__user__username'
    ]
    readonly_fields = [
        'order_number', 'ref', 'amount_value', 
        'created', 'updated'
    ]
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'cart', 'order_status')
        }),
        ('Customer Information', {
            'fields': ('order_by', 'email', 'mobile')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_address', 'shipping_city', 'shipping_state', 
                'shipping_zipcode', 'shipping_country'
            )
        }),
        ('Order Totals', {
            'fields': ('subtotal', 'shipping_cost', 'tax', 'amount')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_complete', 'ref')
        }),
        ('Notes', {
            'fields': ('order_notes',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 50
    
    def amount_value(self, obj):
        return f'{obj.amount_value()} kobo'
    amount_value.short_description = 'Amount (Kobo)'

#::::: ORDER ITEM ADMIN :::::
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'product_price', 'quantity', 'subtotal']
    list_filter = ['order__created']
    search_fields = ['order__order_number', 'product_name']

#::::: HOMEPAGE SECTION ADMIN :::::
@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'section_type', 'order', 'is_active', 'created']
    list_filter = ['section_type', 'is_active', 'created']
    search_fields = ['title', 'description']
    filter_horizontal = ['products', 'categories']
    readonly_fields = ['created', 'updated']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'section_type', 'description', 'image', 'order')
        }),
        ('Content', {
            'fields': ('products', 'categories')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 50