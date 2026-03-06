from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import *

class ProductImageInline(admin.TabularInline):
    model = Product
    fields = ['photo1', 'photo2', 'photo3', 'photo4']
    extra = 0
    max_num = 4
    verbose_name = "Additional Image"
    verbose_name_plural = "Additional Images"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'category_type', 'parent', 'is_active', 'order', 'products_count']
    list_filter = ['category_type', 'is_active', 'is_featured']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['order', 'is_active']
    readonly_fields = ['products_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'image', 'icon')
        }),
        ('Relationships', {
            'fields': ('parent_category', 'parent', 'category_type')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active', 'is_featured', 'show_in_top_100')
        }),
        ('Stats', {
            'fields': ('products_count',),
            'classes': ('collapse',)
        }),
    )
    
    def products_count(self, obj):
        count = obj.get_all_products_count()
        url = reverse('admin:estyecomapp_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} products</a>', url, count)
    products_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'title', 'category', 'price', 'final_price', 'in_stock', 'is_available', 'created']
    list_filter = ['category', 'condition', 'is_available', 'is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival']
    search_fields = ['title', 'description', 'sku']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['price', 'in_stock', 'is_available']
    readonly_fields = ['product_id', 'discount_percentage', 'final_price', 'created', 'updated', 'thumbnail_preview']
    filter_horizontal = ['tags', 'available_sizes']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'short_description', 'sku', 'product_id')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'discount_percentage', 'final_price')
        }),
        ('Images', {
            'fields': ('thumbnail_preview', 'main', 'photo1', 'photo2', 'photo3', 'photo4')
        }),
        ('Categories & Tags', {
            'fields': ('category', 'brand', 'tags', 'condition')
        }),
        ('Inventory', {
            'fields': ('in_stock', 'low_stock_threshold', 'is_available', 'out_of_stock_date', 'restock_date')
        }),
        ('Product Details', {
            'fields': ('color', 'material', 'weight', 'dimensions')
        }),
        ('Features', {
            'fields': ('is_featured', 'is_bestseller', 'is_deal', 'is_new_arrival', 'include_in_top_100')
        }),
        ('Ratings', {
            'fields': ('rating', 'review_count'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    
    def thumbnail(self, obj):
        if obj.main:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.main.url)
        return "No image"
    thumbnail.short_description = 'Image'
    
    def thumbnail_preview(self, obj):
        if obj.main:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.main.url)
        return "No image uploaded"
    thumbnail_preview.short_description = 'Image Preview'
    
    actions = ['mark_as_featured', 'mark_as_bestseller', 'mark_as_deal', 'mark_as_new_arrival']
    
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected as featured"
    
    def mark_as_bestseller(self, request, queryset):
        queryset.update(is_bestseller=True)
    mark_as_bestseller.short_description = "Mark selected as bestseller"
    
    def mark_as_deal(self, request, queryset):
        queryset.update(is_deal=True)
    mark_as_deal.short_description = "Mark selected as deal"
    
    def mark_as_new_arrival(self, request, queryset):
        queryset.update(is_new_arrival=True)
    mark_as_new_arrival.short_description = "Mark selected as new arrival"

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'products_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Products'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'products_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Products'

@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'order']
    list_filter = ['category']
    list_editable = ['order']

@admin.register(GiftOccasion)
class GiftOccasionAdmin(admin.ModelAdmin):
    list_display = ['label', 'date', 'icon', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('label',)}

@admin.register(GiftPersona)
class GiftPersonaAdmin(admin.ModelAdmin):
    list_display = ['name', 'persona_type', 'order', 'is_active']
    list_filter = ['persona_type', 'is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}

# ========== FIXED: Only ONE GiftCollectionAdmin registration ==========
# Create the inline first
class GiftCollectionProductInline(admin.TabularInline):
    model = GiftCollectionProduct
    extra = 1
    fields = ['product', 'display_order', 'is_featured', 'custom_title']
    raw_id_fields = ['product']
    autocomplete_fields = ['product']  # Changed from autocomplete_lookup

# Then register GiftCollection once
@admin.register(GiftCollection)
class GiftCollectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'persona', 'interest_tag', 'order', 'is_active', 'products_count']
    list_filter = ['is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [GiftCollectionProductInline]
    
    def products_count(self, obj):
        return obj.collection_products.count()
    products_count.short_description = 'Products'

@admin.register(GiftRecipient)
class GiftRecipientAdmin(admin.ModelAdmin):
    list_display = ['label', 'icon', 'order', 'is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('label',)}

@admin.register(GiftGridItem)
class GiftGridItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'size', 'order', 'is_active']
    list_filter = ['size', 'is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(GiftInterest)
class GiftInterestAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(PopularGiftCategory)
class PopularGiftCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(GiftGuideSection)
class GiftGuideSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'section_type', 'order', 'is_active']
    list_filter = ['section_type', 'is_active']
    list_editable = ['order']
    filter_horizontal = ['featured_products', 'categories']

@admin.register(GiftTeaserBanner)
class GiftTeaserBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'order', 'is_active']
    list_editable = ['order', 'is_active']

@admin.register(GiftCardBanner)
class GiftCardBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'button_text', 'order', 'is_active']
    list_editable = ['order', 'is_active']

@admin.register(AboutGiftFinder)
class AboutGiftFinderAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_active']
    list_editable = ['is_active']