from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Category, ParentCategory, Top100Gifts

def invalidate_homepage_cache():
    """Invalidate all homepage-related caches"""
    cache.delete_pattern('homepage:*')
    cache.delete('deals:todays')
    cache.delete('top100:data')
    cache.delete('gifts:page')
    cache.delete('giftfinder:data')

def invalidate_product_cache(product_slug=None):
    """Invalidate product-related caches"""
    if product_slug:
        cache.delete(f'product:detail:{product_slug}')
    cache.delete_pattern('products:*')
    cache.delete('deals:todays')
    cache.delete_pattern('homepage:*')

def invalidate_category_cache(category_slug=None):
    """Invalidate category-related caches"""
    if category_slug:
        cache.delete(f'category:detail:{category_slug}')
        cache.delete_pattern(f'category:products:{category_slug}:*')
    cache.delete_pattern('categories:*')
    cache.delete_pattern('homepage:*')

# Signal handlers
@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def product_changed(sender, instance, **kwargs):
    invalidate_product_cache(instance.slug)

@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def category_changed(sender, instance, **kwargs):
    invalidate_category_cache(instance.slug)

@receiver(post_save, sender=ParentCategory)
@receiver(post_delete, sender=ParentCategory)
def parent_category_changed(sender, instance, **kwargs):
    invalidate_homepage_cache()

@receiver(post_save, sender=Top100Gifts)
@receiver(post_delete, sender=Top100Gifts)
def top100_changed(sender, instance, **kwargs):
    cache.delete('top100:data')
    cache.delete_pattern('homepage:*')