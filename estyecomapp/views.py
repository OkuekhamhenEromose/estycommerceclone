from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404, reverse
from django.db import transaction
from django.db.models import Q, Prefetch, Avg  # Added Avg here
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from .serializers import *
from .models import *
import hashlib
import json
import logging
import requests
from django.utils.text import slugify
import os

logger = logging.getLogger(__name__)

# ========== CACHE UTILITY CLASS ==========
class CacheMixin:
    """Mixin to add caching capabilities to views"""
    
    cache_timeout = 300  # 5 minutes default
    
    def get_cache_key(self, request, prefix):
        """Generate unique cache key based on request"""
        params = {
            'path': request.path,
            'query': dict(request.GET.items()),
            'user': 'auth' if request.user.is_authenticated else 'anon',
        }
        key = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()
        return f"{prefix}:{key}"
    
    def get_cached_data(self, key):
        return cache.get(key)
    
    def set_cached_data(self, key, data):
        cache.set(key, data, self.cache_timeout)

# ========== OPTIMIZED PAGINATION ==========
class FastPagination(PageNumberPagination):
    """Optimized pagination with configurable page size"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

# Keep the StandardResultsSetPagination for backward compatibility
class StandardResultsSetPagination(FastPagination):
    """Alias for FastPagination to maintain compatibility"""
    pass

class SimpleHomepageView(APIView):
    """Simple homepage data endpoint that always works"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            "hero_banner": {
                "message": "Find something you love",
                "search_placeholder": "Search for anything"
            },
            "featured_interests": [
                {
                    "id": 1,
                    "title": "Linen Spotlight",
                    "slug": "linen-spotlight",
                    "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=500&fit=crop",
                    "products_count": 156
                },
                {
                    "id": 2,
                    "title": "Mini Gems",
                    "slug": "mini-gems",
                    "image": "https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=400&h=500&fit=crop",
                    "products_count": 89
                }
            ],
            "categories": [
                {
                    "id": 1,
                    "title": "Jewelry",
                    "slug": "jewelry",
                    "image": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=400&fit=crop",
                    "products_count": 245
                },
                {
                    "id": 2,
                    "title": "Home & Living",
                    "slug": "home-living",
                    "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "products_count": 189
                }
            ],
            "todays_deals": [
                {
                    "id": 1,
                    "title": "Handmade Leather Wallet",
                    "slug": "handmade-leather-wallet",
                    "price": 45.99,
                    "discount_price": 29.99,
                    "final_price": 29.99,
                    "discount_percentage": 35,
                    "image": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400&h=400&fit=crop",
                    "rating": 4.8,
                    "review_count": 124,
                    "brand": "LeatherCrafts"
                }
            ],
            "new_arrivals": [],
            "editors_picks": [],
            "top100_gifts": []
        })


# ========== HOMEPAGE VIEW ==========
class HomepageDataView(APIView, CacheMixin):
    """Optimized homepage with Redis caching"""
    permission_classes = [AllowAny]
    cache_timeout = 300  # 5 minutes
    
    @method_decorator(cache_page(300))
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request):
        cache_key = self.get_cache_key(request, 'homepage')
        
        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        try:
            # Safe queries with defaults if tables are empty
            featured_interests = []
            if Category.objects.exists():
                featured_interests = list(
                    Category.objects.filter(
                        category_type='gift_interest',
                        is_featured=True,
                        is_active=True
                    ).select_related('parent').only(
                        'id', 'title', 'slug', 'image', 'order'
                    )[:4]
                )
            
            # Deals
            deals = []
            if Product.objects.exists():
                deals = list(
                    Product.objects.filter(
                        is_deal=True,
                        is_available=True,
                        in_stock__gt=0,
                        discount_price__isnull=False
                    ).select_related('brand', 'category').only(
                        'id', 'title', 'slug', 'price', 'discount_price',
                        'main', 'rating', 'review_count', 'brand__name',
                        'category__title'
                    ).order_by('-discount_price')[:4]
                )
                
                # Calculate discount percentages in Python
                for product in deals:
                    product.discount_percentage = int(
                        ((product.price - product.discount_price) / product.price) * 100
                    ) if product.discount_price else 0
            
            # Main Categories
            categories = []
            if Category.objects.exists():
                categories = list(
                    Category.objects.filter(
                        parent__isnull=True,
                        is_active=True
                    ).select_related('parent_category').only(
                        'id', 'title', 'slug', 'image', 'order'
                    )[:6]
                )
            
            # New Arrivals
            new_arrivals = []
            if Product.objects.exists():
                new_arrivals = list(
                    Product.objects.filter(
                        is_new_arrival=True,
                        is_available=True,
                        in_stock__gt=0
                    ).select_related('brand').only(
                        'id', 'title', 'slug', 'price', 'discount_price',
                        'main', 'rating', 'review_count'
                    ).order_by('-created')[:4]
                )
            
            # Editors Picks (Vintage)
            editors_picks = []
            if Product.objects.exists():
                editors_picks = list(
                    Product.objects.filter(
                        condition='vintage',
                        is_available=True,
                        in_stock__gt=0,
                        rating__gte=4.0
                    ).select_related('brand').only(
                        'id', 'title', 'slug', 'price', 'discount_price',
                        'main', 'rating', 'review_count'
                    ).order_by('-rating')[:4]
                )
            
            # Top 100 Gifts
            top100 = []
            top100_collection = None
            if Top100Gifts.objects.exists():
                top100_collection = Top100Gifts.objects.filter(is_active=True).first()
                if top100_collection:
                    top100 = top100_collection.get_random_selection(8)
            
            # Manual serialization for maximum performance
            data = {
                'hero_banner': {
                    'message': 'Find something you love',
                    'search_placeholder': 'Search for anything'
                },
                'featured_interests': [
                    {
                        'id': c.id,
                        'title': c.title,
                        'slug': c.slug,
                        'image': c.image.url if c.image else None,
                    } for c in featured_interests
                ],
                'categories': [
                    {
                        'id': c.id,
                        'title': c.title,
                        'slug': c.slug,
                        'image': c.image.url if c.image else None,
                    } for c in categories
                ],
                'todays_deals': [
                    {
                        'id': p.id,
                        'title': p.title[:50],
                        'slug': p.slug,
                        'price': float(p.price),
                        'discount_price': float(p.discount_price) if p.discount_price else None,
                        'final_price': float(p.discount_price) if p.discount_price else float(p.price),
                        'discount_percentage': getattr(p, 'discount_percentage', 0),
                        'image': p.main.url if p.main else None,
                        'rating': float(p.rating),
                        'review_count': p.review_count,
                        'brand': p.brand.name if p.brand else None,
                    } for p in deals
                ],
                'new_arrivals': [
                    {
                        'id': p.id,
                        'title': p.title[:50],
                        'slug': p.slug,
                        'price': float(p.price),
                        'discount_price': float(p.discount_price) if p.discount_price else None,
                        'final_price': float(p.discount_price) if p.discount_price else float(p.price),
                        'image': p.main.url if p.main else None,
                        'rating': float(p.rating),
                        'review_count': p.review_count,
                    } for p in new_arrivals
                ],
                'editors_picks': [
                    {
                        'id': p.id,
                        'title': p.title[:50],
                        'slug': p.slug,
                        'price': float(p.price),
                        'discount_price': float(p.discount_price) if p.discount_price else None,
                        'final_price': float(p.discount_price) if p.discount_price else float(p.price),
                        'image': p.main.url if p.main else None,
                        'rating': float(p.rating),
                        'review_count': p.review_count,
                    } for p in editors_picks
                ],
                'top100_gifts': [
                    {
                        'id': p.id,
                        'title': p.title[:50],
                        'slug': p.slug,
                        'price': float(p.price),
                        'discount_price': float(p.discount_price) if p.discount_price else None,
                        'final_price': float(p.discount_price) if p.discount_price else float(p.price),
                        'image': p.main.url if p.main else None,
                        'rating': float(p.rating),
                        'review_count': p.review_count,
                    } for p in top100
                ],
            }
            
            # Cache the result
            self.set_cached_data(cache_key, data)
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("Homepage error")
            return Response({
                'hero_banner': {'message': 'Find something you love'},
                'featured_interests': [],
                'categories': [],
                'todays_deals': [],
                'new_arrivals': [],
                'editors_picks': [],
                'top100_gifts': [],
            }, status=status.HTTP_200_OK)

# ========== CATEGORY VIEWS ==========
class ParentCategoryView(APIView, CacheMixin):
    """List and create parent categories"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'parent-categories')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        parent_categories = ParentCategory.objects.filter(is_active=True).order_by('order')
        serializer = ParentCategorySerializer(parent_categories, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class CategoryView(APIView, CacheMixin):
    """List categories with caching"""
    permission_classes = [AllowAny]
    cache_timeout = 3600  # 1 hour
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'categories')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        categories = Category.objects.filter(is_active=True).select_related('parent').only(
            'id', 'title', 'slug', 'category_type', 'image', 'icon', 
            'order', 'is_active', 'is_featured', 'parent_id'
        )
        
        # Apply filters
        category_type = request.query_params.get('type')
        if category_type:
            categories = categories.filter(category_type=category_type)
        
        parent_category_id = request.query_params.get('parent_category')
        if parent_category_id:
            categories = categories.filter(parent_category_id=parent_category_id)
        
        is_featured = request.query_params.get('featured')
        if is_featured == 'true':
            categories = categories.filter(is_featured=True)
        
        top_level = request.query_params.get('top_level')
        if top_level == 'true':
            categories = categories.filter(parent__isnull=True)
        
        serializer = CategoryListSerializer(categories, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class CategoryDetailView(APIView, CacheMixin):
    """Get single category with caching"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request, slug):
        cache_key = f'category:detail:{slug}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        category = get_object_or_404(
            Category.objects.select_related('parent_category', 'parent'),
            slug=slug,
            is_active=True
        )
        
        serializer = CategoryDetailSerializer(category)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class CategoryProductsView(APIView, CacheMixin):
    """Get category with products"""
    permission_classes = [AllowAny]
    cache_timeout = 600  # 10 minutes
    pagination_class = FastPagination
    
    def get(self, request, slug):
        cache_key = self.get_cache_key(request, f'category:products:{slug}')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        category = get_object_or_404(Category, slug=slug, is_active=True)
        
        # Get products
        products = Product.objects.filter(
            Q(category=category) | Q(category__parent=category),
            is_available=True,
            in_stock__gt=0
        ).select_related('brand').distinct()
        
        # Apply filters
        min_price = request.query_params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        
        max_price = request.query_params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)
        
        # Sorting
        sort_by = request.query_params.get('sort', '-created')
        valid_sorts = ['price', '-price', 'rating', '-rating', 'created', '-created']
        if sort_by in valid_sorts:
            products = products.order_by(sort_by)
        
        # Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(page, many=True)
        
        result = paginator.get_paginated_response(serializer.data).data
        result['category'] = CategoryListSerializer(category).data
        result['total_products'] = products.count()
        
        self.set_cached_data(cache_key, result)
        return Response(result, status=status.HTTP_200_OK)

# ========== PRODUCT VIEWS ==========
class ProductView(APIView, CacheMixin):
    """List products with filtering and pagination"""
    permission_classes = [AllowAny]
    cache_timeout = 600  # 10 minutes
    pagination_class = FastPagination
    
    def get(self, request):
        has_filters = any([
            request.query_params.get('search'),
            request.query_params.get('min_price'),
            request.query_params.get('max_price'),
        ])
        
        if not has_filters:
            cache_key = self.get_cache_key(request, 'products')
            cached = self.get_cached_data(cache_key)
            if cached:
                return Response(cached, status=status.HTTP_200_OK)
        
        products = Product.objects.filter(is_available=True).select_related('category', 'brand')
        
        # Apply filters
        search = request.query_params.get('search')
        if search:
            products = products.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()
        
        category_slug = request.query_params.get('category_slug')
        if category_slug:
            products = products.filter(category__slug=category_slug)
        
        if request.query_params.get('featured') == 'true':
            products = products.filter(is_featured=True)
        if request.query_params.get('deal') == 'true':
            products = products.filter(is_deal=True)
        if request.query_params.get('new') == 'true':
            products = products.filter(is_new_arrival=True)
        
        min_price = request.query_params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        max_price = request.query_params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)
        
        if request.query_params.get('in_stock') == 'true':
            products = products.filter(in_stock__gt=0)
        
        sort_by = request.query_params.get('sort', '-created')
        valid_sorts = ['price', '-price', 'rating', '-rating', 'created', '-created']
        if sort_by in valid_sorts:
            products = products.order_by(sort_by)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(page, many=True)
        
        result = paginator.get_paginated_response(serializer.data).data
        
        if not has_filters:
            self.set_cached_data(cache_key, result)
        
        return Response(result, status=status.HTTP_200_OK)

class ProductDetailView(APIView, CacheMixin):
    """Get single product with caching"""
    permission_classes = [AllowAny]
    cache_timeout = 1800  # 30 minutes
    
    def get(self, request, slug):
        cache_key = f'product:detail:{slug}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        product = get_object_or_404(
            Product.objects.select_related('category', 'brand', 'seller__user'),
            slug=slug,
            is_available=True
        )
        
        serializer = ProductDetailSerializer(product)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== DEALS VIEW ==========
class DealsView(APIView, CacheMixin):
    """Get today's deals with caching"""
    permission_classes = [AllowAny]
    cache_timeout = 300  # 5 minutes
    
    def get(self, request):
        cache_key = 'deals:todays'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        deals = Product.objects.filter(
            is_deal=True,
            is_available=True,
            in_stock__gt=0,
            discount_price__isnull=False
        ).select_related('brand').only(
            'id', 'title', 'slug', 'price', 'discount_price',
            'main', 'rating', 'review_count', 'brand__name'
        ).order_by('-discount_price')[:20]
        
        # Calculate discount in Python
        data = []
        for d in deals:
            discount = int(((d.price - d.discount_price) / d.price) * 100)
            data.append({
                'id': d.id,
                'title': d.title[:50],
                'slug': d.slug,
                'price': float(d.price),
                'discount_price': float(d.discount_price),
                'final_price': float(d.discount_price),
                'discount_percentage': discount,
                'image': d.main.url if d.main else None,
                'rating': float(d.rating),
                'review_count': d.review_count,
                'brand': d.brand.name if d.brand else None,
            })
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== TOP 100 GIFTS VIEW ==========
class Top100GiftsView(APIView, CacheMixin):
    """Get Top 100 Gifts collection"""
    permission_classes = [AllowAny]
    cache_timeout = 1800  # 30 minutes
    
    def get(self, request):
        cache_key = 'top100:data'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        collection = Top100Gifts.objects.filter(is_active=True).first()
        if not collection:
            return Response({'products': []}, status=status.HTTP_200_OK)
        
        if collection.auto_populate:
            collection.populate_products()
        
        random_selection = request.query_params.get('random', 'false')
        if random_selection == 'true':
            count = int(request.query_params.get('count', 20))
            products = collection.get_random_selection(count)
        else:
            products = collection.products.filter(is_available=True, in_stock__gt=0)[:20]
        
        serializer = ProductListSerializer(products, many=True)
        data = {
            'title': collection.title,
            'description': collection.description,
            'products': serializer.data
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== NAVIGATION VIEW ==========
class NavigationView(APIView, CacheMixin):
    """Get complete navigation structure"""
    permission_classes = [AllowAny]
    cache_timeout = 3600  # 1 hour
    
    def get(self, request):
        cache_key = 'navigation:data'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        data = {
            'parent_categories': ParentCategorySerializer(
                ParentCategory.objects.filter(is_active=True).order_by('order'), 
                many=True
            ).data,
            'gift_occasions': CategoryListSerializer(
                Category.objects.filter(category_type='gift_occasion', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'gift_interests': CategoryListSerializer(
                Category.objects.filter(category_type='gift_interest', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'gift_popular': CategoryListSerializer(
                Category.objects.filter(category_type='gift_popular', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'fashion_finds': CategoryListSerializer(
                Category.objects.filter(category_type='fashion_finds', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'home_favourites': CategoryListSerializer(
                Category.objects.filter(category_type='home_favourites', is_active=True).order_by('order')[:8],
                many=True
            ).data,
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== GIFT FINDER VIEW ==========
class GiftFinderDataView(APIView, CacheMixin):
    """Get all data for Gift Finder page"""
    permission_classes = [AllowAny]
    cache_timeout = 3600  # 1 hour
    
    def get(self, request):
        cache_key = 'giftfinder:data'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        data = {
            'hero_occasions': GiftOccasionSerializer(
                GiftOccasion.objects.filter(is_active=True).order_by('order'), 
                many=True
            ).data,
            'browse_interests': GiftInterestSerializer(
                GiftInterest.objects.filter(is_active=True).order_by('order'),
                many=True
            ).data,
            'featured_collections': GiftCollectionSerializer(
                GiftCollection.objects.filter(is_active=True).select_related('persona').order_by('order')[:2],
                many=True
            ).data,
            'recipients': GiftRecipientSerializer(
                GiftRecipient.objects.filter(is_active=True).prefetch_related('items').order_by('order')[:2],
                many=True
            ).data,
            'gift_personas': GiftPersonaSerializer(
                GiftPersona.objects.filter(persona_type='interest', is_active=True).order_by('order')[:10],
                many=True
            ).data,
            'guilty_pleasures': GiftPersonaSerializer(
                GiftPersona.objects.filter(persona_type='guilty_pleasure', is_active=True).order_by('order')[:5],
                many=True
            ).data,
            'zodiac_signs': GiftPersonaSerializer(
                GiftPersona.objects.filter(persona_type='zodiac_sign', is_active=True).order_by('order')[:5],
                many=True
            ).data,
            'gift_grid_items': GiftGridItemSerializer(
                GiftGridItem.objects.filter(is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'popular_gift_categories': PopularGiftCategorySerializer(
                PopularGiftCategory.objects.filter(is_active=True).order_by('order'),
                many=True
            ).data,
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== GIFTS PAGE VIEW ==========
class GiftsPageDataView(APIView, CacheMixin):
    """Get gifts page data"""
    permission_classes = [AllowAny]
    cache_timeout = 1800  # 30 minutes
    
    def get(self, request):
        cache_key = 'gifts:page'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        data = {
            'best_gift_guides': GiftGuideSectionSerializer(
                GiftGuideSection.objects.filter(
                    section_type='best_gift_guides', 
                    is_active=True
                ).prefetch_related('gift_products__product').order_by('order')[:5],
                many=True
            ).data,
            'valentines_gifts': GiftGuideSectionSerializer(
                GiftGuideSection.objects.filter(
                    section_type='valentines_gifts', 
                    is_active=True
                ).prefetch_related('gift_products__product').order_by('order')[:1],
                many=True
            ).data,
            'bestselling_gifts': GiftGuideSectionSerializer(
                GiftGuideSection.objects.filter(
                    section_type='bestselling_gifts', 
                    is_active=True
                ).prefetch_related('gift_products__product').order_by('order')[:1],
                many=True
            ).data,
            'personalized_presents': GiftGuideSectionSerializer(
                GiftGuideSection.objects.filter(
                    section_type='personalized_presents', 
                    is_active=True
                ).prefetch_related('gift_products__product').order_by('order')[:1],
                many=True
            ).data,
            'gift_occasions': CategoryListSerializer(
                Category.objects.filter(category_type='gift_occasion', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'gift_interests': CategoryListSerializer(
                Category.objects.filter(category_type='gift_interest', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'gift_popular': CategoryListSerializer(
                Category.objects.filter(category_type='gift_popular', is_active=True).order_by('order')[:8],
                many=True
            ).data,
            'top_rated_products': ProductListSerializer(
                Product.objects.filter(
                    rating__gte=4.0, is_available=True, in_stock__gt=0
                ).order_by('-rating', '-review_count')[:20],
                many=True
            ).data,
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class GiftGuideSectionDetailView(APIView, CacheMixin):
    """Get specific gift guide section with products"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request, section_type):
        cache_key = f'gift:section:{section_type}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        section = get_object_or_404(
            GiftGuideSection,
            section_type=section_type,
            is_active=True
        )
        
        gift_products = section.gift_products.select_related('product').order_by('display_order')
        
        if gift_products.exists():
            products = [gp.product for gp in gift_products]
        elif section.featured_products.exists():
            products = section.featured_products.filter(
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand')[:20]
        else:
            products = Product.objects.filter(
                is_available=True,
                in_stock__gt=0
            ).order_by('-rating')[:20]
        
        data = {
            'section': GiftGuideSectionSerializer(section).data,
            'products': ProductListSerializer(products, many=True).data
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class GiftCategoryProductsView(APIView, CacheMixin):
    """Get products for specific gift category"""
    pagination_class = FastPagination
    permission_classes = [AllowAny]
    cache_timeout = 600
    
    def get(self, request, category_slug):
        cache_key = self.get_cache_key(request, f'gift:category:{category_slug}')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        category = get_object_or_404(
            Category.objects.filter(
                Q(category_type__in=['gifts', 'gift_occasion', 'gift_interest', 'gift_popular']) |
                Q(title__icontains='gift'),
                is_active=True
            ),
            slug=category_slug
        )
        
        products = Product.objects.filter(
            Q(category=category) | Q(category__parent=category),
            is_available=True,
            in_stock__gt=0
        ).distinct().select_related('brand')
        
        # Apply filters
        min_price = request.query_params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        max_price = request.query_params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)
        
        # Sort
        sort_by = request.query_params.get('sort', '-rating')
        if sort_by == 'price':
            products = products.order_by('price')
        elif sort_by == '-price':
            products = products.order_by('-price')
        else:
            products = products.order_by('-rating', '-review_count')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)
        
        result = paginator.get_paginated_response(ProductListSerializer(page, many=True).data).data
        result['category'] = CategoryDetailSerializer(category).data
        result['total_products'] = products.count()
        
        self.set_cached_data(cache_key, result)
        return Response(result, status=status.HTTP_200_OK)

# ========== BEST OF VALENTINE VIEW ==========
class BestOfValentineView(APIView, CacheMixin):
    """Get Best of Valentine's Day page data"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'valentine:data')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        valentine_section = GiftGuideSection.objects.filter(
            section_type='best_of_valentine',
            is_active=True
        ).first()
        
        if not valentine_section:
            valentine_section = GiftGuideSection.objects.create(
                title="Best of Valentine's Day",
                section_type='best_of_valentine',
                description="Picks you'll love",
                is_active=True
            )
        
        # Get Valentine's Day categories
        valentine_categories = Category.objects.filter(
            Q(title__icontains='valentine') |
            Q(description__icontains='valentine') |
            Q(title__icontains='heart') |
            Q(title__icontains='love'),
            is_active=True
        ).distinct()[:10]
        
        # If no categories found, provide default ones
        categories_data = []
        if valentine_categories.exists():
            categories_data = CategoryListSerializer(valentine_categories, many=True).data
        else:
            # Create default categories if needed (or return empty array)
            categories_data = []
        
        # Get Valentine's Day products
        products = Product.objects.filter(
            Q(title__icontains='valentine') |
            Q(description__icontains='valentine') |
            Q(tags__name__icontains='valentine') |
            Q(title__icontains='heart') |
            Q(title__icontains='love') |
            Q(category__title__icontains='valentine'),
            is_available=True,
            in_stock__gt=0
        ).distinct().select_related('category', 'brand')[:20]
        
        products_data = ProductListSerializer(products, many=True).data
        
        # ALWAYS include related_searches, even if empty
        related_searches = [
            "valentines day gifts",
            "romantic gifts for him",
            "romantic gifts for her",
            "heart jewellery",
            "personalised valentines",
            "valentines day cards",
            "chocolate gifts",
            "date night ideas",
            "anniversary gifts",
            "love themed decor"
        ]
        
        # Apply filters from request
        price_filter = request.query_params.get('price', 'any')
        on_sale = request.query_params.get('on_sale', 'false') == 'true'
        etsy_picks = request.query_params.get('etsy_picks', 'false') == 'true'
        sort_by = request.query_params.get('sort', 'relevance')
        
        # Filter products based on query params (simplified for now)
        filtered_products = products_data
        if on_sale:
            filtered_products = [p for p in filtered_products if p.get('discount_price')]
        if etsy_picks:
            filtered_products = [p for p in filtered_products if p.get('etsy_pick')]
        
        data = {
            'section': GiftGuideSectionSerializer(valentine_section).data,
            'categories': categories_data,
            'products': filtered_products,
            'related_searches': related_searches,  # Always include this
            'filters': {
                'price_options': [
                    {'value': 'any', 'label': 'Any price'},
                    {'value': 'under25', 'label': 'Under $25'},
                    {'value': '25to50', 'label': '$25 to $50'},
                    {'value': '50to100', 'label': '$50 to $100'},
                    {'value': 'over100', 'label': 'Over $100'},
                ],
                'sort_options': [
                    {'value': 'relevance', 'label': 'Relevance'},
                    {'value': 'low_to_high', 'label': 'Price: Low to High'},
                    {'value': 'high_to_low', 'label': 'Price: High to Low'},
                    {'value': 'top_rated', 'label': 'Top Rated'},
                ],
                'shipping_options': [
                    {'value': 'anywhere', 'label': 'Anywhere'},
                    {'value': 'US', 'label': 'United States'},
                    {'value': 'UK', 'label': 'United Kingdom'},
                    {'value': 'CA', 'label': 'Canada'},
                    {'value': 'AU', 'label': 'Australia'},
                ]
            },
            'current_filters': {
                'price': price_filter,
                'on_sale': on_sale,
                'etsy_picks': etsy_picks,
                'sort': sort_by
            }
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

class ProductUploadView(APIView):
    """
    API view for uploading products with images
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can upload
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            # Create product instance
            data = request.data.copy()
            
            # Generate slug if not provided
            if 'slug' not in data or not data['slug']:
                data['slug'] = slugify(data.get('title', ''))
            
            # Handle main image
            if 'main' in request.FILES:
                data['main'] = request.FILES['main']
            
            # Handle additional images
            for i in range(1, 5):
                field_name = f'photo{i}'
                if field_name in request.FILES:
                    data[field_name] = request.FILES[field_name]
            
            # Set seller to current user
            data['seller'] = request.user.profile.id if hasattr(request.user, 'profile') else None
            
            serializer = ProductSerializer(data=data)
            if serializer.is_valid():
                product = serializer.save()
                
                # Clear relevant caches
                cache.delete(CacheKeys.HOMEPAGE)
                cache.delete(CacheKeys.DEALS)
                
                return Response({
                    'message': 'Product created successfully',
                    'product': ProductDetailSerializer(product).data
                }, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, product_id):
        """Update an existing product"""
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Check if user is the seller
            if product.seller and product.seller.user != request.user:
                return Response({'error': 'You do not have permission to edit this product'}, 
                              status=status.HTTP_403_FORBIDDEN)
            
            data = request.data.copy()
            
            # Handle image updates
            if 'main' in request.FILES:
                data['main'] = request.FILES['main']
            
            for i in range(1, 5):
                field_name = f'photo{i}'
                if field_name in request.FILES:
                    data[field_name] = request.FILES[field_name]
            
            serializer = ProductSerializer(product, data=data, partial=True)
            if serializer.is_valid():
                product = serializer.save()
                
                # Clear caches
                cache.delete(CacheKeys.product(product.slug))
                cache.delete(CacheKeys.HOMEPAGE)
                cache.delete(CacheKeys.DEALS)
                
                return Response({
                    'message': 'Product updated successfully',
                    'product': ProductDetailSerializer(product).data
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========== HOME FAVOURITES VIEW ==========
class HomeFavouritesView(APIView, CacheMixin):
    """Get Home Favourites page data"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'home:favourites')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        home_favourites_section = HomepageSection.objects.filter(
            section_type='home_favourites',
            is_active=True
        ).first()
        
        if not home_favourites_section:
            home_favourites_section = HomepageSection.objects.create(
                title="Etsy's Guide to Home",
                section_type='home_favourites',
                description="Discover original wall art, comfy bedding, unique lighting, and more from small shops.",
                is_active=True,
                order=0
            )
        
        # Get Home Favourites categories
        home_categories = Category.objects.filter(
            category_type='home_favourites',
            is_active=True
        )[:6]
        
        # If no categories found, create default ones
        if not home_categories.exists():
            default_home_categories = [
                "Artisanal Dinnerware",
                "Outdoor Furniture & Decor",
                "Garden Decor & Supplies",
                "Personalised Home Decor",
                "Candles & Home Fragrance",
                "Vintage Home Decor"
            ]
            
            for title in default_home_categories:
                Category.objects.get_or_create(
                    title=title,
                    defaults={
                        'slug': slugify(title),
                        'category_type': 'home_favourites',
                        'is_active': True
                    }
                )
            home_categories = Category.objects.filter(category_type='home_favourites', is_active=True)[:6]
        
        # Get hero categories (featured categories for the hero section)
        hero_categories = Category.objects.filter(
            Q(is_featured=True) | Q(category_type='home_favourites'),
            is_active=True
        ).distinct()[:6]
        
        # If no hero categories, use some defaults
        hero_categories_data = []
        if hero_categories.exists():
            for cat in hero_categories:
                hero_categories_data.append({
                    'title': cat.title,
                    'image': cat.image.url if cat.image else None,
                    'slug': cat.slug
                })
        else:
            # Default hero categories
            hero_categories_data = [
                {
                    'title': 'Home Decor',
                    'image': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop',
                    'slug': 'home-decor'
                },
                {
                    'title': 'Kitchen & Dining',
                    'image': 'https://images.unsplash.com/photo-1548625320-cf6858a7c538?w=400&h=400&fit=crop',
                    'slug': 'kitchen-dining'
                },
                {
                    'title': 'Furniture',
                    'image': 'https://images.unsplash.com/photo-1567016376408-0226e1d3d0c6?w=400&h=400&fit=crop',
                    'slug': 'furniture'
                },
                {
                    'title': 'Vintage Rugs',
                    'image': 'https://images.unsplash.com/photo-1519710164239-da123dc03ef4?w=400&h=400&fit=crop',
                    'slug': 'vintage-rugs'
                },
                {
                    'title': 'Lighting',
                    'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=400&fit=crop',
                    'slug': 'lighting'
                },
                {
                    'title': 'Bedding',
                    'image': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&h=400&fit=crop',
                    'slug': 'bedding'
                }
            ]
        
        # Get products for Home Favourites sections
        # Spring-ready linens products
        spring_linens_products = Product.objects.filter(
            Q(title__icontains='linen') |
            Q(description__icontains='linen') |
            Q(category__title__icontains='linen') |
            Q(category__title__icontains='bedding'),
            is_available=True,
            in_stock__gt=0
        ).distinct()[:8]
        
        # Reorganizing products
        reorganizing_products = Product.objects.filter(
            Q(title__icontains='organizer') |
            Q(title__icontains='storage') |
            Q(title__icontains='organize') |
            Q(description__icontains='organizer') |
            Q(description__icontains='storage'),
            is_available=True,
            in_stock__gt=0
        ).distinct()[:8]
        
        # Small shops data
        shops_data = [
            {
                "name": "OliveLaneInteriors",
                "rating": 5,
                "reviewCount": "100",
                "images": [
                    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1548625320-cf6858a7c538?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1567016376408-0226e1d3d0c6?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=400&fit=crop"
                ]
            },
            {
                "name": "BrooxFurniture",
                "rating": 5,
                "reviewCount": "116",
                "images": [
                    "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1548625320-cf6858a7c538?w=400&h=400&fit=crop"
                ]
            },
            {
                "name": "ForestlandLinen",
                "rating": 5,
                "reviewCount": "4,977",
                "images": [
                    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1567016376408-0226e1d3d0c6?w=400&h=400&fit=crop"
                ]
            },
            {
                "name": "MDTMobilier",
                "rating": 3,
                "reviewCount": "70",
                "images": [
                    "https://images.unsplash.com/photo-1548625320-cf6858a7c538?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "https://images.unsplash.com/photo-1548625320-cf6858a7c538?w=400&h=400&fit=crop"
                ]
            }
        ]
        
        # Discover more categories
        discover_categories = [
            {
                "title": "Special Starts on Etsy",
                "image": "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=400&h=400&fit=crop",
                "slug": "special-starts"
            },
            {
                "title": "Global Seller Spotlight",
                "image": "https://images.unsplash.com/photo-1567016376408-0226e1d3d0c6?w=400&h=400&fit=crop",
                "slug": "global-seller"
            },
            {
                "title": "Vintage Home Decor",
                "image": "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?w=400&h=400&fit=crop",
                "slug": "vintage-home-decor"
            },
            {
                "title": "Explore Unique Wall Art",
                "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                "slug": "unique-wall-art"
            }
        ]
        
        response_data = {
            "section": {
                "id": home_favourites_section.id,
                "title": home_favourites_section.title,
                "description": home_favourites_section.description,
                "section_type": home_favourites_section.section_type,
            },
            "hero_categories": hero_categories_data,
            "home_categories": CategoryListSerializer(home_categories, many=True).data,
            "small_shops": shops_data,
            "spring_linens_products": ProductListSerializer(spring_linens_products, many=True).data,
            "reorganizing_products": ProductListSerializer(reorganizing_products, many=True).data,
            "discover_categories": discover_categories,
            "filters": {
                "price_options": [
                    {"value": "any", "label": "Any price"},
                    {"value": "under25", "label": "Under USD 25"},
                    {"value": "25to50", "label": "USD 25 to USD 50"},
                    {"value": "50to100", "label": "USD 50 to USD 100"},
                    {"value": "over100", "label": "Over USD 100"}
                ]
            }

        }
        
        self.set_cached_data(cache_key, response_data)
        return Response(response_data, status=status.HTTP_200_OK)

# ========== FASHION FINDS VIEW ==========
class FashionFindsView(APIView, CacheMixin):
    """Get Fashion Finds page data"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'fashion:finds')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        fashion_section = HomepageSection.objects.filter(
            section_type='fashion_finds',
            is_active=True
        ).first()
        
        if not fashion_section:
            fashion_section = HomepageSection.objects.create(
                title="Etsy's Guide to Fashion",
                section_type='fashion_finds',
                description="From custom clothing to timeless jewellery, everything you need to upgrade your wardrobe.",
                is_active=True,
                order=0
            )
        
        # Get Fashion Finds categories
        fashion_categories = Category.objects.filter(
            Q(category_type='fashion_finds') |
            Q(title__icontains='clothing') |
            Q(title__icontains='jewel') |
            Q(title__icontains='accessor'),
            is_active=True
        ).distinct()[:12]
        
        # If no categories, provide default ones
        if not fashion_categories.exists():
            # Create default categories or return empty list
            fashion_categories = []
        
        # Get Fashion Shops We Love
        fashion_shops = FashionShop.objects.filter(
            is_featured=True
        ).prefetch_related('featured_products').order_by('order')[:4]
        
        # If no shops exist, provide default mock shops
        if not fashion_shops.exists():
            # Create default shops data directly in the response
            fashion_shops_data = [
                {
                    "id": 1,
                    "name": "SbriStudio",
                    "slug": "sbristudio",
                    "rating": 5.0,
                    "review_count": 2841,
                    "display_name": "Sbristudio",
                    "description": "Handmade fashion items",
                    "is_featured": True,
                    "order": 0,
                    "featured_products_preview": []
                },
                {
                    "id": 2,
                    "name": "Plexida",
                    "slug": "plexida",
                    "rating": 5.0,
                    "review_count": 2092,
                    "display_name": "Plexida",
                    "description": "Unique fashion accessories",
                    "is_featured": True,
                    "order": 1,
                    "featured_products_preview": []
                },
                {
                    "id": 3,
                    "name": "GemBlue",
                    "slug": "gemblue",
                    "rating": 5.0,
                    "review_count": 2473,
                    "display_name": "GemBlue",
                    "description": "Jewellery and accessories",
                    "is_featured": True,
                    "order": 2,
                    "featured_products_preview": []
                },
                {
                    "id": 4,
                    "name": "LetterParty",
                    "slug": "letterparty",
                    "rating": 5.0,
                    "review_count": 273,
                    "display_name": "LetterParty",
                    "description": "Personalised fashion items",
                    "is_featured": True,
                    "order": 3,
                    "featured_products_preview": []
                }
            ]
        else:
            fashion_shops_data = FashionShopSerializer(fashion_shops, many=True).data
        
        # Get personalised clothes products
        personalised_clothes = Product.objects.filter(
            Q(title__icontains='personalised') |
            Q(title__icontains='custom') |
            Q(title__icontains='embroidered'),
            is_available=True,
            in_stock__gt=0
        ).distinct().order_by('-rating')[:20]
        
        # If no products, provide mock products
        if not personalised_clothes.exists():
            personalised_clothes_products_data = [
                {
                    "id": 1,
                    "title": "Custom Embroidered Portrait from Photo",
                    "slug": "custom-embroidered-portrait",
                    "short_description": "Custom embroidery portrait from your photo",
                    "price": 15.48,
                    "discount_price": 25.8,
                    "discount_percentage": 40,
                    "final_price": 15.48,
                    "main": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=400&h=500&fit=crop",
                    "rating": 4.7,
                    "review_count": 3200,
                    "is_featured": True,
                    "is_bestseller": True,
                    "is_deal": True,
                    "is_new_arrival": False,
                    "condition": "handmade",
                    "color": "White",
                    "shop_name": "TypeCityCo",
                    "etsy_pick": True,
                    "freeDelivery": False,
                    "has_video": False
                }
            ]
        else:
            personalised_clothes_products_data = ProductListSerializer(personalised_clothes, many=True).data
        
        # Get unique handbags products
        unique_handbags = Product.objects.filter(
            Q(title__icontains='handbag') |
            Q(title__icontains='purse') |
            Q(title__icontains='tote') |
            Q(title__icontains='bag'),
            is_available=True,
            in_stock__gt=0
        ).distinct().order_by('-rating')[:20]
        
        if not unique_handbags.exists():
            unique_handbags_products_data = [
                {
                    "id": 101,
                    "title": "Black Handwoven Leather Purse - Adjustable",
                    "slug": "black-handwoven-leather-purse",
                    "short_description": "Handwoven leather purse with adjustable strap",
                    "price": 75.0,
                    "discount_price": None,
                    "discount_percentage": 0,
                    "final_price": 75.0,
                    "main": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop",
                    "rating": 4.8,
                    "review_count": 892,
                    "is_featured": True,
                    "is_bestseller": False,
                    "is_deal": False,
                    "is_new_arrival": False,
                    "condition": "handmade",
                    "color": "Black",
                    "shop_name": "LeatherCraftCo",
                    "etsy_pick": True,
                    "freeDelivery": True,
                    "has_video": False
                }
            ]
        else:
            unique_handbags_products_data = ProductListSerializer(unique_handbags, many=True).data
        
        # Get personalised jewellery products
        personalised_jewellery = Product.objects.filter(
            Q(title__icontains='jewellery') |
            Q(title__icontains='jewelry') |
            Q(title__icontains='necklace') |
            Q(title__icontains='ring') |
            Q(title__icontains='bracelet'),
            is_available=True,
            in_stock__gt=0
        ).distinct().order_by('-rating')[:20]
        
        if not personalised_jewellery.exists():
            personalised_jewellery_products_data = [
                {
                    "id": 201,
                    "title": "Personalized gold plated secret locket necklace",
                    "slug": "personalized-gold-locket",
                    "short_description": "Gold plated secret locket necklace",
                    "price": 221.56,
                    "discount_price": None,
                    "discount_percentage": 0,
                    "final_price": 221.56,
                    "main": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=500&fit=crop",
                    "rating": 4.9,
                    "review_count": 186,
                    "is_featured": True,
                    "is_bestseller": True,
                    "is_deal": False,
                    "is_new_arrival": False,
                    "condition": "handmade",
                    "color": "Gold",
                    "shop_name": "Isabellebshop",
                    "etsy_pick": True,
                    "freeDelivery": True,
                    "has_video": False
                }
            ]
        else:
            personalised_jewellery_products_data = ProductListSerializer(personalised_jewellery, many=True).data
        
        # Get promo cards
        promo_cards = FashionPromoCard.objects.filter(
            is_active=True
        ).order_by('order')[:2]
        
        if not promo_cards.exists():
            promo_cards_data = [
                {
                    "id": 1,
                    "title": "Elevate your everyday jewellery",
                    "subtitle": "Discover unique pieces",
                    "description": "Find jewellery that complements your style",
                    "image": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&h=400&fit=crop",
                    "button_text": "Shop now",
                    "button_url": "/jewellery",
                    "order": 0,
                    "is_active": True
                },
                {
                    "id": 2,
                    "title": "The Charm Shop",
                    "subtitle": "Personalised charms",
                    "description": "Create your own charm collection",
                    "image": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&h=400&fit=crop",
                    "button_text": "Shop now",
                    "button_url": "/charms",
                    "order": 1,
                    "is_active": True
                }
            ]
        else:
            promo_cards_data = FashionPromoCardSerializer(promo_cards, many=True).data
        
        # Get trending section
        trending = FashionTrending.objects.filter(
            is_active=True
        )[:1]
        
        if not trending.exists():
            trending_data = [
                {
                    "id": 1,
                    "title": "Trending now: Burgundy hues",
                    "subtitle": "Winter collection",
                    "description": "Jump into one of our favourite colours for winter. The deep shade will bring a moody vibe to any outfit as we move into chillier temperatures.",
                    "image": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&h=600&fit=crop",
                    "button_text": "Try it out",
                    "button_url": "/trending/burgundy",
                    "is_active": True
                }
            ]
        else:
            trending_data = FashionTrendingSerializer(trending, many=True).data
        
        # Get discover more section
        discover_more = FashionDiscover.objects.filter(
            is_active=True
        ).order_by('order')[:4]
        
        if not discover_more.exists():
            discover_more_data = [
                {
                    "id": 1,
                    "title": "Special Starts on Etsy",
                    "image": "https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=400&h=400&fit=crop",
                    "url": "/special-starts",
                    "order": 0,
                    "is_active": True
                },
                {
                    "id": 2,
                    "title": "The Linen Shop",
                    "image": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=400&fit=crop",
                    "url": "/linen-shop",
                    "order": 1,
                    "is_active": True
                },
                {
                    "id": 3,
                    "title": "The Personalisation Shop",
                    "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
                    "url": "/personalisation-shop",
                    "order": 2,
                    "is_active": True
                },
                {
                    "id": 4,
                    "title": "Etsy's Guide to Vintage",
                    "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
                    "url": "/vintage-guide",
                    "order": 3,
                    "is_active": True
                }
            ]
        else:
            discover_more_data = FashionDiscoverSerializer(discover_more, many=True).data
        
        data = {
            'hero_title': fashion_section.title,
            'hero_description': fashion_section.description,
            'hero_categories': CategoryListSerializer(fashion_categories, many=True).data,
            'shops_we_love': fashion_shops_data,
            'personalised_clothes_products': personalised_clothes_products_data,
            'unique_handbags_products': unique_handbags_products_data,
            'personalised_jewellery_products': personalised_jewellery_products_data,
            'promo_cards': promo_cards_data,
            'trending': trending_data,
            'discover_more': discover_more_data,
            'filters': {
                'price_options': [
                    {'value': 'any', 'label': 'Any price'},
                    {'value': 'under25', 'label': 'Under USD 25'},
                    {'value': '25to50', 'label': 'USD 25 to USD 50'},
                    {'value': '50to100', 'label': 'USD 50 to USD 100'},
                    {'value': 'over100', 'label': 'Over USD 100'}
                ]
            }
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)


# ========== GIFT TEASER VIEW ==========
class GiftTeaserDataView(APIView, CacheMixin):
    """Get gift teaser and gift card data"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = 'gift:teaser'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        teaser_banner = GiftTeaserBanner.objects.filter(
            is_active=True
        ).prefetch_related('features').order_by('order').first()
        
        gift_card_banner = GiftCardBanner.objects.filter(
            is_active=True
        ).order_by('order').first()
        
        about_section = AboutGiftFinder.objects.filter(
            is_active=True
        ).first()
        
        data = {
            'teaser_banner': GiftTeaserBannerSerializer(teaser_banner).data if teaser_banner else None,
            'gift_card_banner': GiftCardBannerSerializer(gift_card_banner).data if gift_card_banner else None,
            'about_section': AboutGiftFinderSerializer(about_section).data if about_section else None,
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== BRAND VIEW ==========
class BrandView(APIView, CacheMixin):
    """List brands"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'brands')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        brands = Brand.objects.filter(is_active=True).order_by('name')
        serializer = BrandSerializer(brands, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== TAG VIEW ==========
class TagView(APIView, CacheMixin):
    """List tags"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'tags')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        tags = Tag.objects.all().order_by('name')
        serializer = TagSerializer(tags, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== PRODUCT SIZE VIEW ==========
class ProductSizeView(APIView, CacheMixin):
    """List product sizes"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'sizes')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        sizes = ProductSize.objects.all()
        
        category = request.query_params.get('category')
        if category:
            sizes = sizes.filter(category=category)
        
        serializer = ProductSizeSerializer(sizes, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== REVIEW VIEWS ==========
class ProductReviewView(APIView):
    """Product review operations"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug)
        reviews = product.reviews.select_related('user__user').order_by('-created')
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug)
        serializer = ProductReviewSerializer(data=request.data)
        
        if serializer.is_valid():
            existing_review = ProductReview.objects.filter(
                product=product,
                user=request.user.profile
            ).first()
            
            if existing_review:
                return Response(
                    {'error': 'You have already reviewed this product'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            review = serializer.save(product=product, user=request.user.profile)
            
            # Update product rating
            avg_rating = ProductReview.objects.filter(product=product).aggregate(
                Avg('rating')
            )['rating__avg']
            product.rating = round(avg_rating, 2) if avg_rating else 0
            product.review_count = ProductReview.objects.filter(product=product).count()
            product.save()
            
            # Clear cache
            cache.delete(f'prod:reviews:{product.id}')
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ========== WISHLIST VIEWS ==========
class WishlistView(APIView):
    """User wishlist operations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user.profile)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user.profile)
        
        if product in wishlist.products.all():
            return Response({'message': 'Product already in wishlist'}, status=status.HTTP_400_BAD_REQUEST)
        
        wishlist.products.add(product)
        cache.delete(f'wishlist:{request.user.profile.id}')
        return Response({'message': 'Product added to wishlist'}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        wishlist = get_object_or_404(Wishlist, user=request.user.profile)
        
        if product not in wishlist.products.all():
            return Response({'error': 'Product not in wishlist'}, status=status.HTTP_400_BAD_REQUEST)
        
        wishlist.products.remove(product)
        cache.delete(f'wishlist:{request.user.profile.id}')
        return Response({'message': 'Product removed from wishlist'}, status=status.HTTP_200_OK)

# ========== CART VIEWS ==========
class AddToCartView(APIView):
    """Add product to cart"""
    permission_classes = [AllowAny]
    
    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_available=True)
        
        if product.in_stock <= 0:
            return Response({'error': 'Product out of stock'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_id = request.session.get('cart_id')
        quantity = int(request.data.get('quantity', 1))
        size_id = request.data.get('size_id')
        
        with transaction.atomic():
            if cart_id:
                cart = Cart.objects.filter(id=cart_id).first()
                if not cart:
                    cart = Cart.objects.create(total=0)
                    request.session['cart_id'] = cart.id
            else:
                cart = Cart.objects.create(total=0)
                request.session['cart_id'] = cart.id
            
            if request.user.is_authenticated and hasattr(request.user, 'profile'):
                cart.profile = request.user.profile
                cart.save()
            
            selected_size = ProductSize.objects.filter(id=size_id).first() if size_id else None
            
            cart_product = cart.items.filter(product=product, selected_size=selected_size).first()
            
            if cart_product:
                new_quantity = cart_product.quantity + quantity
                if new_quantity > product.in_stock:
                    return Response({'error': f'Only {product.in_stock} items available'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                cart_product.quantity = new_quantity
                cart_product.save()
                message = 'Item quantity updated in cart'
            else:
                if quantity > product.in_stock:
                    return Response({'error': f'Only {product.in_stock} items available'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                cart_product = CartProduct.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity,
                    selected_size=selected_size
                )
                message = 'Item added to cart'
            
            cart.update_total()
            
            serializer = CartSerializer(cart)
            return Response({'message': message, 'cart': serializer.data}, status=status.HTTP_200_OK)

class MyCartView(APIView):
    """Get user cart"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            return Response({'cart': None, 'items': [], 'total': 0}, status=status.HTTP_200_OK)
        
        cart = Cart.objects.filter(id=cart_id).first()
        if not cart:
            return Response({'cart': None, 'items': [], 'total': 0}, status=status.HTTP_200_OK)
        
        if request.user.is_authenticated and hasattr(request.user, 'profile') and not cart.profile:
            cart.profile = request.user.profile
            cart.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ManageCartView(APIView):
    """Manage cart items"""
    permission_classes = [AllowAny]
    
    def post(self, request, id):
        action = request.data.get('action')
        cart_product = get_object_or_404(CartProduct, id=id)
        cart = cart_product.cart
        product = cart_product.product
        
        if action == "inc":
            if cart_product.quantity + 1 > product.in_stock:
                return Response({'error': f'Only {product.in_stock} items available'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            cart_product.quantity += 1
            cart_product.save()
            cart.update_total()
            return Response({'message': 'Item quantity increased'}, status=status.HTTP_200_OK)
        
        elif action == "dcr":
            cart_product.quantity -= 1
            if cart_product.quantity == 0:
                cart_product.delete()
                message = 'Item removed from cart'
            else:
                cart_product.save()
                message = 'Item quantity decreased'
            cart.update_total()
            return Response({'message': message}, status=status.HTTP_200_OK)
        
        elif action == 'rmv':
            cart_product.delete()
            cart.update_total()
            return Response({'message': 'Item removed from cart'}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

# ========== CHECKOUT VIEW ==========
class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            return Response({'error': 'Cart not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = get_object_or_404(Cart, id=cart_id)
            
            if not cart.items.exists():
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
            
            for item in cart.items.all():
                if item.quantity > item.product.in_stock:
                    return Response(
                        {'error': f'Insufficient stock for {item.product.title}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            serializer = CheckoutSerializer(data=request.data)
            
            if serializer.is_valid():
                with transaction.atomic():
                    order = serializer.save(
                        cart=cart,
                        user=request.user.profile,
                        amount=cart.total,
                        subtotal=cart.total,
                        order_status='pending'
                    )
                    
                    for cart_item in cart.items.all():
                        size_name = cart_item.selected_size.code if cart_item.selected_size else None
                        
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            product_name=cart_item.product.title,
                            product_price=cart_item.product.final_price,
                            quantity=cart_item.quantity,
                            selected_size=size_name,
                            subtotal=cart_item.subtotal
                        )
                        
                        product = cart_item.product
                        product.in_stock -= cart_item.quantity
                        product.save()
                    
                    del request.session['cart_id']
                    
                    if order.payment_method == 'paystack':
                        payment_url = reverse('payment', args=[order.id])
                        return Response({
                            'message': 'Order created successfully',
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'redirect_url': payment_url
                        }, status=status.HTTP_201_CREATED)
                    
                    return Response({
                        'message': 'Order created successfully',
                        'order_id': order.id,
                        'order_number': order.order_number
                    }, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========== PAYMENT VIEWS ==========
class PaymentPageView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            order = get_object_or_404(Order, id=id, user=request.user.profile)
            
            if order.payment_complete:
                return Response({'message': 'Payment already completed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize Paystack payment
            url = "https://api.paystack.co/transaction/initialize"
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            data = {
                "amount": order.amount_value(),
                "email": order.email,
                "reference": order.ref
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response_data = response.json()
            
            if response_data.get("status"):
                paystack_url = response_data["data"]["authorization_url"]
                
                return Response({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'amount': float(order.amount),
                    'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
                    'paystack_url': paystack_url,
                    'reference': order.ref
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Payment initiation failed'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentView(APIView):
    def get(self, request, ref):
        try:
            order = get_object_or_404(Order, ref=ref)
            
            # Verify payment with Paystack
            url = f'https://api.paystack.co/transaction/verify/{ref}'
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            response = requests.get(url, headers=headers, timeout=10)
            response_data = response.json()
            
            if response_data.get("status") and response_data["data"]["status"] == "success":
                paid_amount = response_data["data"]["amount"] / 100
                
                if paid_amount == float(order.amount):
                    order.payment_complete = True
                    order.order_status = 'processing'
                    order.save()
                    
                    return Response({
                        'message': 'Payment verified successfully',
                        'order_number': order.order_number
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'Payment amount mismatch'}, status=status.HTTP_400_BAD_REQUEST)
                    
            elif response_data["data"]["status"] == "abandoned":
                order.order_status = "pending"
                order.save()
                return Response({'error': 'Payment abandoned, please try again'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Payment verification failed'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Order.DoesNotExist:
            return Response({'error': 'Invalid payment reference'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========== ORDER VIEWS ==========
class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            orders = Order.objects.filter(user=request.user.profile).order_by('-created')
            serializer = OrderListSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_number):
        try:
            order = get_object_or_404(
                Order,
                order_number=order_number,
                user=request.user.profile
            )
            serializer = OrderDetailSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========== HOMEPAGE SECTIONS VIEW ==========
class HomepageSectionsView(APIView, CacheMixin):
    """Get all homepage sections"""
    permission_classes = [AllowAny]
    cache_timeout = 3600
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'homepage-sections')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        sections = HomepageSection.objects.filter(is_active=True).order_by('order')
        serializer = HomepageSectionSerializer(sections, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== CATEGORY GROUPS VIEW ==========
class CategoryGroupsView(APIView, CacheMixin):
    """Get organized category groups with their products"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        cache_key = self.get_cache_key(request, 'category-groups')
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        category_type = request.query_params.get('type')
        
        if category_type:
            categories = Category.objects.filter(
                category_type=category_type,
                is_active=True
            )
        else:
            categories = Category.objects.filter(
                category_type__in=['gifts', 'fashion_finds', 'home_favourites'],
                is_active=True
            )
        
        result = []
        for category in categories:
            all_products = category.get_all_products(limit=20)
            featured = [p for p in all_products if p.is_featured][:10]
            top_rated = category.get_top_rated_products(limit=10)
            
            result.append({
                'category': CategoryDetailSerializer(category).data,
                'featured_products': ProductListSerializer(featured, many=True).data,
                'top_rated_products': ProductListSerializer(top_rated, many=True).data,
                'product_count': len(all_products)
            })
        
        self.set_cached_data(cache_key, result)
        return Response(result, status=status.HTTP_200_OK)

# ========== COMPONENT SPECIFIC DATA VIEW ==========
class ComponentSpecificDataView(APIView, CacheMixin):
    """Get specific data for each homepage component"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        component = request.query_params.get('component')
        
        if not component:
            return Response({'error': 'Component parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f'component:{component}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        try:
            if component == 'featured_interests':
                categories = Category.objects.filter(
                    category_type='gift_interest',
                    is_featured=True,
                    is_active=True
                )[:10]
                serializer = CategoryListSerializer(categories, many=True)
                data = serializer.data
                
            elif component == 'birthday_gifts':
                categories = Category.objects.filter(
                    Q(title__icontains='birthday'),
                    is_active=True
                )[:6]
                
                products = Product.objects.filter(
                    Q(title__icontains='birthday') |
                    Q(tags__name__icontains='birthday'),
                    is_available=True,
                    in_stock__gt=0
                ).distinct()[:12]
                
                data = {
                    'categories': CategoryListSerializer(categories, many=True).data,
                    'products': ProductListSerializer(products, many=True).data
                }
                
            elif component == 'todays_deals':
                data = DealsView().get(request).data
                
            elif component == 'categories':
                categories = Category.objects.filter(
                    parent__isnull=True,
                    is_active=True
                )[:8]
                
                result = []
                for category in categories:
                    subcategories = category.subcategories.filter(is_active=True)[:5]
                    products = Product.objects.filter(
                        category=category,
                        is_available=True,
                        in_stock__gt=0
                    )[:8]
                    
                    category_data = CategoryListSerializer(category).data
                    category_data['subcategories'] = CategoryListSerializer(subcategories, many=True).data
                    category_data['featured_products'] = ProductListSerializer(products, many=True).data
                    result.append(category_data)
                
                return Response(result, status=status.HTTP_200_OK)
                
            else:
                return Response({'error': 'Invalid component specified'}, status=status.HTTP_400_BAD_REQUEST)
            
            self.set_cached_data(cache_key, data)
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========== HOMEPAGE SECTION PRODUCTS VIEW ==========
class HomepageSectionProductsView(APIView, CacheMixin):
    """Get products for specific homepage section"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request, section_type):
        cache_key = f'section:products:{section_type}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        section = get_object_or_404(
            HomepageSection, 
            section_type=section_type,
            is_active=True
        )
        
        if section.products.exists():
            products = section.products.filter(
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand')[:20]
        else:
            products = Product.objects.filter(
                is_available=True,
                in_stock__gt=0
            ).order_by('-rating')[:20]
        
        data = {
            'section': HomepageSectionSerializer(section).data,
            'products': ProductListSerializer(products, many=True).data
        }
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== GIFT COLLECTION BY INTEREST VIEW ==========
class GiftCollectionByInterestView(APIView, CacheMixin):
    """Get gift collections filtered by interest"""
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        interest = request.query_params.get('interest', 'Jewellery')
        cache_key = f'collections:interest:{interest}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        collections = GiftCollection.objects.filter(
            interest_tag=interest,
            is_active=True
        ).prefetch_related(
            Prefetch('collection_products', queryset=GiftCollectionProduct.objects.select_related('product')),
            'persona'
        ).order_by('order')[:2]
        
        if not collections.exists():
            collections = GiftCollection.objects.filter(is_active=True).order_by('order')[:2]
        
        serializer = GiftCollectionSerializer(collections, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== POPULAR GIFTS BY CATEGORY VIEW ==========
class PopularGiftsByCategoryView(APIView, CacheMixin):
    """Get popular gifts filtered by category"""
    pagination_class = FastPagination
    permission_classes = [AllowAny]
    cache_timeout = 1800
    
    def get(self, request):
        category = request.query_params.get('category', 'Jewellery')
        cache_key = f'popular:gifts:{category}'
        
        cached = self.get_cached_data(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        
        products = Product.objects.filter(
            Q(category__title__icontains=category) |
            Q(title__icontains=category) |
            Q(tags__name__icontains=category),
            is_available=True,
            in_stock__gt=0
        ).distinct().order_by('-rating', '-review_count')[:8]
        
        if not products.exists():
            products = Product.objects.filter(
                is_available=True,
                in_stock__gt=0
            ).order_by('-rating', '-review_count')[:8]
        
        serializer = ProductListSerializer(products, many=True)
        data = serializer.data
        
        self.set_cached_data(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)

# ========== MARK ORDER AS GIFT VIEW ==========
class MarkOrderAsGiftView(APIView):
    """Mark a cart item as a gift"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            return Response({'error': 'No active cart found'}, status=status.HTTP_404_NOT_FOUND)
        
        cart = get_object_or_404(Cart, id=cart_id)
        cart_product_id = request.data.get('cart_product_id')
        
        if not cart_product_id:
            return Response({'error': 'Cart product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_product = get_object_or_404(CartProduct, id=cart_product_id, cart=cart)
        
        if not hasattr(cart, 'metadata') or cart.metadata is None:
            cart.metadata = {}
        
        if 'gift_items' not in cart.metadata:
            cart.metadata['gift_items'] = []
        
        if cart_product.id not in cart.metadata['gift_items']:
            cart.metadata['gift_items'].append(cart_product.id)
            cart.save()
        
        return Response({
            'message': 'Item marked as gift',
            'cart_product_id': cart_product.id
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            return Response({'error': 'No active cart found'}, status=status.HTTP_404_NOT_FOUND)
        
        cart = get_object_or_404(Cart, id=cart_id)
        cart_product_id = request.data.get('cart_product_id')
        
        if not cart_product_id:
            return Response({'error': 'Cart product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if hasattr(cart, 'metadata') and cart.metadata and 'gift_items' in cart.metadata:
            if cart_product_id in cart.metadata['gift_items']:
                cart.metadata['gift_items'].remove(cart_product_id)
                cart.save()
        
        return Response({
            'message': 'Item unmarked as gift',
            'cart_product_id': cart_product_id
        }, status=status.HTTP_200_OK)