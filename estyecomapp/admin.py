from django.contrib import admin
from django.utils.html import format_html
from .models import *

#::::: PARENT CATEGORY ADMIN :::::
@admin.register(ParentCategory)
class ParentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'is_featured', 'product_count_display', 'created']
    list_filter = ['is_active', 'is_featured', 'created']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active', 'is_featured']
    
    def product_count_display(self, obj):
        return obj.get_product_count()
    product_count_display.short_description = 'Total Products'

#::::: CATEGORY ADMIN :::::
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'slug', 'category_type', 'parent', 'parent_category', 
        'order', 'is_active', 'is_featured', 'show_in_top_100', 'products_count_display'
    ]
    list_filter = [
        'category_type', 'is_active', 'is_featured', 'show_in_top_100',
        'parent_category', 'created'
    ]
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['order', 'title']
    list_per_page = 50
    list_editable = ['order', 'is_active', 'is_featured', 'show_in_top_100']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category_type', 'description', 'image', 'icon')
        }),
        ('Relationships', {
            'fields': ('parent_category', 'parent')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active', 'is_featured', 'show_in_top_100')
        }),
    )
    
    def products_count_display(self, obj):
        return obj.get_all_products_count()
    products_count_display.short_description = 'Products Count'

#::::: PRODUCT SIZE ADMIN :::::
@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ['category', 'name', 'code', 'order']
    list_filter = ['category']
    search_fields = ['name', 'code']
    ordering = ['category', 'order', 'name']
    list_editable = ['order']

#::::: TAG ADMIN :::::
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'products_count_display', 'created']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def products_count_display(self, obj):
        return obj.products.filter(is_available=True).count()
    products_count_display.short_description = 'Products'

#::::: BRAND ADMIN :::::
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'products_count_display', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    def products_count_display(self, obj):
        return obj.products.filter(is_available=True).count()
    products_count_display.short_description = 'Products'

#::::: PRODUCT ADMIN :::::
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'slug', 'category', 'brand', 'price', 
        'discount_price', 'condition', 'stock_status', 'rating_display',
        'is_available', 'is_featured', 'is_bestseller', 'is_deal', 
        'is_new_arrival', 'include_in_top_100', 'created'
    ]
    list_filter = [
        'category', 'brand', 'condition', 'is_available', 
        'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival',
        'include_in_top_100', 'color', 'created'
    ]
    search_fields = ['title', 'slug', 'description', 'sku']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags', 'available_sizes']
    readonly_fields = ['product_id', 'rating', 'review_count', 'created', 'updated']
    list_editable = ['is_available', 'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival', 'include_in_top_100']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'short_description', 'category', 'brand', 'tags', 'seller')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Images', {
            'fields': ('main', 'photo1', 'photo2', 'photo3', 'photo4')
        }),
        ('Inventory', {
            'fields': ('sku', 'in_stock', 'low_stock_threshold', 'condition', 'out_of_stock_date', 'restock_date')
        }),
        ('Physical Attributes', {
            'fields': ('available_sizes', 'color', 'material', 'weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Status & Features', {
            'fields': ('is_available', 'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival', 'include_in_top_100')
        }),
        ('Ratings & Reviews', {
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
    
    def stock_status(self, obj):
        if obj.in_stock == 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.is_low_stock:
            color = 'orange'
            status = f'Low Stock ({obj.in_stock})'
        else:
            color = 'green'
            status = f'In Stock ({obj.in_stock})'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, status
        )
    stock_status.short_description = 'Stock Status'
    
    def rating_display(self, obj):
        stars = '⭐' * int(obj.rating)
        return format_html(
            '{} <small>({} reviews)</small>',
            stars, obj.review_count
        )
    rating_display.short_description = 'Rating'

#::::: TOP 100 GIFTS ADMIN :::::
@admin.register(Top100Gifts)
class Top100GiftsAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'auto_populate', 'products_count_display', 'updated']
    list_filter = ['is_active', 'auto_populate', 'created']
    filter_horizontal = ['products']
    readonly_fields = ['created', 'updated']
    actions = ['populate_collection']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'is_active', 'auto_populate')
        }),
        ('Products', {
            'fields': ('products',)
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    
    def products_count_display(self, obj):
        return obj.products.count()
    products_count_display.short_description = 'Products Count'
    
    def populate_collection(self, request, queryset):
        for collection in queryset:
            collection.populate_products()
        self.message_user(request, f"Successfully populated {queryset.count()} collection(s)")
    populate_collection.short_description = "Populate with top products"

#::::: PRODUCT REVIEW ADMIN :::::
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating_display', 'is_verified_purchase', 'helpful_count', 'created']
    list_filter = ['rating', 'is_verified_purchase', 'created']
    search_fields = ['product__title', 'user__user__username', 'comment']
    readonly_fields = ['created', 'updated']
    list_per_page = 50
    
    def rating_display(self, obj):
        stars = '⭐' * obj.rating
        return stars
    rating_display.short_description = 'Rating'

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
    fields = ['product', 'quantity', 'selected_size', 'subtotal']

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
    list_display = ['cart', 'product', 'selected_size', 'quantity', 'subtotal', 'created']
    list_filter = ['created']
    search_fields = ['cart__id', 'product__title']
    readonly_fields = ['subtotal', 'created', 'updated']

#::::: ORDER ITEM INLINE :::::
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'quantity', 'selected_size', 'subtotal']
    fields = ['product', 'product_name', 'product_price', 'quantity', 'selected_size', 'subtotal']

#::::: ORDER ADMIN :::::
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
        'order_number', 'ref', 'amount_value_display', 
        'created', 'updated'
    ]
    inlines = [OrderItemInline]
    list_editable = ['order_status', 'payment_complete']
    
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
            'fields': ('subtotal', 'shipping_cost', 'tax', 'amount', 'amount_value_display')
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
    
    def amount_value_display(self, obj):
        return f'{obj.amount_value()} kobo'
    amount_value_display.short_description = 'Amount (Kobo)'


#::::: ORDER ITEM ADMIN :::::
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'selected_size', 'product_price', 'quantity', 'subtotal']
    list_filter = ['order__created']
    search_fields = ['order__order_number', 'product_name']
    readonly_fields = ['created', 'updated']

#::::: HOMEPAGE SECTION ADMIN :::::
@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'section_type', 'order', 'is_active', 'created']
    list_filter = ['section_type', 'is_active', 'created']
    search_fields = ['title', 'description']
    filter_horizontal = ['products', 'categories']
    readonly_fields = ['created', 'updated']
    list_editable = ['order', 'is_active']
    
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