from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from django.shortcuts import reverse, get_object_or_404
from django.db import transaction
from django.db.models import Q, Avg, Count, Prefetch, F, ExpressionWrapper, DecimalField
from django.conf import settings

import requests
from .serializers import *
from .models import *
import random
from django.utils.text import slugify

# :::::::::::::::::::  HOMEPAGE DATA VIEWS  :::::::::::::::::
class HomepageDataView(APIView):
    """Get all data needed for homepage in a single optimized query"""
    def get(self, request):
        try:
            data = {}
            
            # Use select_related and prefetch_related for optimization
            sections = HomepageSection.objects.filter(
                is_active=True
            ).order_by('order').prefetch_related(
                Prefetch('products', queryset=Product.objects.filter(is_available=True, in_stock__gt=0)),
                'categories'
            )
            
            # Handle empty sections gracefully
            if sections.exists():
                data['homepage_sections'] = HomepageSectionSerializer(sections, many=True).data
            else:
                data['homepage_sections'] = []
            
            # Get deals products with discount percentage calculation
            deals_products = Product.objects.filter(
                is_deal=True, 
                is_available=True,
                in_stock__gt=0,
                discount_price__isnull=False
            ).annotate(
                discount_percent=ExpressionWrapper(
                    (F('price') - F('discount_price')) * 100 / F('price'),
                    output_field=DecimalField(max_digits=5, decimal_places=2)
                )
            ).filter(discount_percent__gt=0).order_by('-discount_percent')[:20]
            
            # Get featured products
            featured_products = Product.objects.filter(
                is_featured=True,
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand')[:20]
            
            # Get bestseller products
            bestseller_products = Product.objects.filter(
                is_bestseller=True,
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand')[:20]
            
            # Get new arrival products (created in last 30 days)
            from django.utils import timezone
            month_ago = timezone.now() - timezone.timedelta(days=30)
            new_arrival_products = Product.objects.filter(
                is_new_arrival=True,
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand')[:20]
            
            # Get gift categories
            gift_categories = Category.objects.filter(
                category_type__in=['gifts', 'gift_occasion', 'gift_interest'],
                is_active=True
            ).prefetch_related('subcategories')[:8]
            
            # Get birthday categories
            birthday_categories = Category.objects.filter(
                Q(category_type='gift_occasion') & 
                (Q(title__icontains='birthday') | Q(description__icontains='birthday')),
                is_active=True
            )[:6]
            
            # Get birthday products
            birthday_products = Product.objects.filter(
                Q(title__icontains='birthday') |
                Q(description__icontains='birthday') |
                Q(tags__name__icontains='birthday'),
                is_available=True,
                in_stock__gt=0
            ).distinct()[:12]
            
            # Get vintage products for editor's picks
            vintage_products = Product.objects.filter(
                condition='vintage',
                is_available=True,
                in_stock__gt=0
            ).select_related('category', 'brand').order_by('-rating')[:15]
            
            # Get featured interests categories
            featured_interests = Category.objects.filter(
                category_type='gift_interest',
                is_featured=True,
                is_active=True
            )[:8]
            
            # Get discover section categories (top-level)
            discover_categories = Category.objects.filter(
                parent__isnull=True,
                is_active=True
            ).prefetch_related('subcategories')[:8]
            
            # Get top 100 gifts
            top100_products = []
            top100_collection = Top100Gifts.objects.filter(is_active=True).first()
            if top100_collection:
                if top100_collection.auto_populate:
                    try:
                        top100_collection.populate_products()
                    except:
                        pass  # Skip if population fails
                top100_products = top100_collection.get_random_selection(20)
            
            # Get main categories with subcategories and products
            main_categories = Category.objects.filter(
                parent__isnull=True,
                is_active=True
            )[:8]
            
            categories_with_details = []
            for category in main_categories:
                subcategories = category.subcategories.filter(is_active=True)[:5]
                products = Product.objects.filter(
                    category=category,
                    is_available=True,
                    in_stock__gt=0
                ).select_related('category', 'brand')[:8]
                
                category_data = CategoryListSerializer(category).data
                category_data['subcategories'] = CategoryListSerializer(subcategories, many=True).data
                category_data['featured_products'] = ProductListSerializer(products, many=True).data
                categories_with_details.append(category_data)
            
            data.update({
                'hero_banner': {
                    'message': 'Find something you love',
                    'image': None,
                    'search_placeholder': 'Search for anything'
                },
                'featured_interests': CategoryListSerializer(featured_interests, many=True).data,
                'discover_section': CategoryListSerializer(discover_categories, many=True).data,
                'birthday_gifts': {
                    'categories': CategoryListSerializer(birthday_categories, many=True).data,
                    'products': ProductListSerializer(birthday_products, many=True).data
                },
                'gift_categories': CategoryListSerializer(gift_categories, many=True).data,
                'categories': categories_with_details,
                'todays_deals': ProductListSerializer(deals_products, many=True).data,
                'editors_picks_vintage': ProductListSerializer(vintage_products, many=True).data,
                'top100_gifts': ProductListSerializer(top100_products, many=True).data,
                'featured_products': ProductListSerializer(featured_products, many=True).data,
                'bestseller_products': ProductListSerializer(bestseller_products, many=True).data,
                'new_arrival_products': ProductListSerializer(new_arrival_products, many=True).data,
            })
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            # Return a more detailed error
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch homepage data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestHomepageView(APIView):
    """Simple test endpoint to debug the homepage data"""
    def get(self, request):
        try:
            # Test basic response
            return Response({
                'status': 'success',
                'message': 'API is working',
                'endpoint': '/homepage/',
                'test_data': {
                    'categories_count': Category.objects.count(),
                    'products_count': Product.objects.count(),
                    'sections_count': HomepageSection.objects.count()
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
class ComponentSpecificDataView(APIView):
    """Get specific data for each homepage component"""
    
    def get(self, request):
        component = request.query_params.get('component', None)
        
        try:
            if component == 'featured_interests':
                categories = Category.objects.filter(
                    category_type='gift_interest',
                    is_featured=True,
                    is_active=True
                ).prefetch_related('subcategories')[:10]
                serializer = CategoryListSerializer(categories, many=True)
                
            elif component == 'birthday_gifts':
                categories = Category.objects.filter(
                    Q(title__icontains='birthday') |
                    Q(description__icontains='birthday'),
                    is_active=True
                )[:6]
                
                products = Product.objects.filter(
                    Q(title__icontains='birthday') |
                    Q(description__icontains='birthday') |
                    Q(tags__name__icontains='birthday'),
                    is_available=True,
                    in_stock__gt=0
                ).distinct()[:12]
                
                data = {
                    'categories': CategoryListSerializer(categories, many=True).data,
                    'products': ProductListSerializer(products, many=True).data
                }
                return Response(data, status=status.HTTP_200_OK)
                
            elif component == 'gift_categories':
                categories = Category.objects.filter(
                    category_type__in=['gifts', 'gift_occasion', 'gift_interest', 'gift_popular'],
                    is_active=True
                ).prefetch_related('subcategories')[:12]
                serializer = CategoryListSerializer(categories, many=True)
                
            elif component == 'todays_deals':
                # Get deals with discount > 20%
                products = Product.objects.filter(
                    is_deal=True,
                    is_available=True,
                    in_stock__gt=0,
                    discount_price__isnull=False
                ).annotate(
                    discount_percent=ExpressionWrapper(
                        (F('price') - F('discount_price')) * 100 / F('price'),
                        output_field=DecimalField(max_digits=5, decimal_places=2)
                    )
                ).filter(discount_percent__gt=20).order_by('-discount_percent')[:20]
                
                serializer = ProductListSerializer(products, many=True)
                
            elif component == 'editors_picks_vintage':
                products = Product.objects.filter(
                    condition='vintage',
                    is_available=True,
                    in_stock__gt=0,
                    rating__gte=4.0
                ).select_related('category', 'brand').order_by('-rating')[:15]
                serializer = ProductListSerializer(products, many=True)
                
            elif component == 'categories':
                categories = Category.objects.filter(
                    parent__isnull=True,
                    is_active=True
                ).prefetch_related('subcategories')[:8]
                
                result = []
                for category in categories:
                    subcategories = category.subcategories.filter(is_active=True)[:5]
                    products = Product.objects.filter(
                        category=category,
                        is_available=True,
                        in_stock__gt=0
                    ).select_related('category', 'brand')[:8]
                    
                    category_data = CategoryListSerializer(category).data
                    category_data['subcategories'] = CategoryListSerializer(subcategories, many=True).data
                    category_data['featured_products'] = ProductListSerializer(products, many=True).data
                    result.append(category_data)
                
                return Response(result, status=status.HTTP_200_OK)
                
            else:
                return Response(
                    {'error': 'Invalid component specified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomepageSectionProductsView(APIView):
    """Get products for specific homepage section"""
    
    def get(self, request, section_type):
        try:
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
                # Auto-generate products based on section type
                if section_type == 'big_deals':
                    products = Product.objects.filter(
                        is_deal=True,
                        is_available=True,
                        in_stock__gt=0,
                        discount_price__isnull=False
                    ).annotate(
                        discount_percent=ExpressionWrapper(
                            (F('price') - F('discount_price')) * 100 / F('price'),
                            output_field=DecimalField(max_digits=5, decimal_places=2)
                        )
                    ).filter(discount_percent__gt=15).order_by('-discount_percent')[:20]
                elif section_type == 'featured_interests':
                    products = Product.objects.filter(
                        category__category_type='gift_interest',
                        category__is_featured=True,
                        is_available=True,
                        in_stock__gt=0
                    ).distinct()[:20]
                elif section_type == 'vintage_guide':
                    products = Product.objects.filter(
                        condition='vintage',
                        is_available=True,
                        in_stock__gt=0
                    )[:20]
                else:
                    products = Product.objects.filter(
                        is_available=True,
                        in_stock__gt=0
                    ).select_related('category', 'brand').order_by('-rating')[:20]
            
            serializer = ProductListSerializer(products, many=True)
            
            return Response({
                'section': HomepageSectionSerializer(section).data,
                'products': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CUSTOM PAGINATION :::::
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

#::::: PARENT CATEGORY VIEWS :::::
class ParentCategoryView(APIView):
    """List and create parent categories"""
    def get(self, request):
        try:
            parent_categories = ParentCategory.objects.filter(is_active=True)
            serializer = ParentCategorySerializer(parent_categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            serializer = ParentCategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CATEGORY VIEWS :::::
class CategoryView(APIView):
    """List all categories with filtering options"""
    def get(self, request):
        try:
            categories = Category.objects.filter(is_active=True)
            
            # Filter by type
            category_type = request.query_params.get('type', None)
            if category_type:
                categories = categories.filter(category_type=category_type)
            
            # Filter by parent category
            parent_category_id = request.query_params.get('parent_category', None)
            if parent_category_id:
                categories = categories.filter(parent_category_id=parent_category_id)
            
            # Filter featured
            is_featured = request.query_params.get('featured', None)
            if is_featured == 'true':
                categories = categories.filter(is_featured=True)
            
            # Get top-level categories only (no parent)
            top_level = request.query_params.get('top_level', None)
            if top_level == 'true':
                categories = categories.filter(parent__isnull=True)
            
            serializer = CategoryListSerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            serializer = CategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryDetailView(APIView):
    """Get, update, and delete specific category"""
    def get(self, request, slug):
        try:
            category = get_object_or_404(Category, slug=slug, is_active=True)
            serializer = CategoryDetailSerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, slug):
        try:
            category = get_object_or_404(Category, slug=slug)
            serializer = CategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, slug):
        try:
            category = get_object_or_404(Category, slug=slug)
            category.delete()
            return Response({"message": "Category deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CATEGORY WITH PRODUCTS VIEW :::::
class CategoryProductsView(APIView):
    """Get category with all its products"""
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, slug):
        try:
            category = get_object_or_404(Category, slug=slug, is_active=True)
            
            # Get all products including from subcategories
            products = Product.objects.filter(
                Q(category=category) | Q(category__parent=category),
                is_available=True
            ).distinct()
            
            # Apply filters
            min_price = request.query_params.get('min_price', None)
            max_price = request.query_params.get('max_price', None)
            if min_price:
                products = products.filter(price__gte=min_price)
            if max_price:
                products = products.filter(price__lte=max_price)
            
            # Sort
            sort_by = request.query_params.get('sort', '-created')
            products = products.order_by(sort_by)
            
            # Pagination
            paginator = self.pagination_class()
            paginated_products = paginator.paginate_queryset(products, request)
            
            response_data = {
                'category': CategoryDetailSerializer(category).data,
                'products': ProductListSerializer(paginated_products, many=True).data,
                'total_products': products.count()
            }
            
            return paginator.get_paginated_response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: NAVIGATION STRUCTURE VIEW :::::
class NavigationView(APIView):
    """Get complete navigation structure for frontend"""
    def get(self, request):
        try:
            data = {
                'parent_categories': ParentCategory.objects.filter(is_active=True),
                'gift_occasions': Category.objects.filter(
                    category_type='gift_occasion', 
                    is_active=True
                ),
                'gift_interests': Category.objects.filter(
                    category_type='gift_interest', 
                    is_active=True
                ),
                'gift_recipients': Category.objects.filter(
                    category_type='gift_recipient', 
                    is_active=True
                ),
                'gift_popular': Category.objects.filter(
                    category_type='gift_popular', 
                    is_active=True
                ),
                'gifts_section': Category.objects.filter(
                    category_type='gifts',
                    is_active=True
                ),
                'fashion_finds': Category.objects.filter(
                    category_type='fashion_finds',
                    is_active=True
                ),
                'home_favourites': Category.objects.filter(
                    category_type='home_favourites',
                    is_active=True
                ),
            }
            
            serializer = NavigationSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: TOP 100 GIFTS VIEW :::::
class Top100GiftsView(APIView):
    """Get Top 100 Gifts collection"""
    def get(self, request):
        try:
            # Get or create the Top 100 collection
            collection = Top100Gifts.objects.filter(is_active=True).first()
            
            if not collection:
                return Response(
                    {'message': 'Top 100 Gifts collection not available'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Auto-populate if needed
            if collection.auto_populate:
                collection.populate_products()
            
            # Check if requesting random selection
            random_selection = request.query_params.get('random', 'false')
            
            if random_selection == 'true':
                count = int(request.query_params.get('count', 20))
                serializer = Top100GiftsRandomSerializer(
                    collection,
                    context={'random_count': count}
                )
            else:
                serializer = Top100GiftsSerializer(collection)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: PRODUCT VIEWS :::::
class ProductView(APIView):
    """List all products with advanced filtering and pagination"""
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        try:
            products = Product.objects.filter(is_available=True)
            
            # Search by title or description
            search = request.query_params.get('search', None)
            if search:
                products = products.filter(
                    Q(title__icontains=search) | 
                    Q(description__icontains=search) |
                    Q(short_description__icontains=search) |
                    Q(tags__name__icontains=search)
                ).distinct()
            
            # Filter by category
            category_id = request.query_params.get('category', None)
            if category_id:
                products = products.filter(category_id=category_id)
            
            # Filter by category slug
            category_slug = request.query_params.get('category_slug', None)
            if category_slug:
                products = products.filter(category__slug=category_slug)
            
            # Filter by brand
            brand_id = request.query_params.get('brand', None)
            if brand_id:
                products = products.filter(brand_id=brand_id)
            
            # Filter by tags
            tag_slug = request.query_params.get('tag', None)
            if tag_slug:
                products = products.filter(tags__slug=tag_slug)
            
            # Filter by condition
            condition = request.query_params.get('condition', None)
            if condition:
                products = products.filter(condition=condition)
            
            # Filter by color
            color = request.query_params.get('color', None)
            if color:
                products = products.filter(color__icontains=color)
            
            # Filter featured products
            is_featured = request.query_params.get('featured', None)
            if is_featured == 'true':
                products = products.filter(is_featured=True)
            
            # Filter bestsellers
            is_bestseller = request.query_params.get('bestseller', None)
            if is_bestseller == 'true':
                products = products.filter(is_bestseller=True)
            
            # Filter deals
            is_deal = request.query_params.get('deal', None)
            if is_deal == 'true':
                products = products.filter(is_deal=True)
            
            # Filter new arrivals
            is_new = request.query_params.get('new_arrival', None)
            if is_new == 'true':
                products = products.filter(is_new_arrival=True)
            
            # Filter in stock only
            in_stock_only = request.query_params.get('in_stock', None)
            if in_stock_only == 'true':
                products = products.filter(in_stock__gt=0)
            
            # Price range filter
            min_price = request.query_params.get('min_price', None)
            max_price = request.query_params.get('max_price', None)
            if min_price:
                products = products.filter(price__gte=min_price)
            if max_price:
                products = products.filter(price__lte=max_price)
            
            # Rating filter
            min_rating = request.query_params.get('min_rating', None)
            if min_rating:
                products = products.filter(rating__gte=min_rating)
            
            # Sorting
            sort_by = request.query_params.get('sort', '-created')
            valid_sorts = [
                'price', '-price', 'title', '-title', 
                'rating', '-rating', 'created', '-created',
                'review_count', '-review_count'
            ]
            if sort_by in valid_sorts:
                products = products.order_by(sort_by)
            
            # Pagination
            paginator = self.pagination_class()
            paginated_products = paginator.paginate_queryset(products, request)
            serializer = ProductListSerializer(paginated_products, many=True)
            
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            serializer = ProductSerializer(data=request.data)
            if serializer.is_valid():
                # Set seller if authenticated
                if request.user.is_authenticated and hasattr(request.user, 'profile'):
                    serializer.save(seller=request.user.profile)
                else:
                    serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductDetailView(APIView):
    """Get, update, and delete specific product"""
    def get(self, request, slug):
        try:
            product = get_object_or_404(Product, slug=slug, is_available=True)
            serializer = ProductDetailSerializer(product)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, slug):
        try:
            product = get_object_or_404(Product, slug=slug)
            serializer = ProductSerializer(product, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, slug):
        try:
            product = get_object_or_404(Product, slug=slug)
            product.delete()
            return Response({"message": "Product deleted"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: PRODUCT REVIEW VIEWS :::::
class ProductReviewView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, product_slug):
        try:
            product = get_object_or_404(Product, slug=product_slug)
            reviews = ProductReview.objects.filter(product=product)
            serializer = ProductReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, product_slug):
        try:
            product = get_object_or_404(Product, slug=product_slug)
            serializer = ProductReviewSerializer(data=request.data)
            
            if serializer.is_valid():
                # Check if user already reviewed
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
                
                # Update product rating and review count
                avg_rating = ProductReview.objects.filter(product=product).aggregate(
                    Avg('rating')
                )['rating__avg']
                product.rating = round(avg_rating, 2) if avg_rating else 0
                product.review_count = ProductReview.objects.filter(product=product).count()
                product.save()
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: WISHLIST VIEWS :::::
class WishlistView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            wishlist, created = Wishlist.objects.get_or_create(user=request.user.profile)
            serializer = WishlistSerializer(wishlist)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Add product to wishlist"""
        try:
            product_id = request.data.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            wishlist, created = Wishlist.objects.get_or_create(user=request.user.profile)
            
            if product in wishlist.products.all():
                return Response(
                    {'message': 'Product already in wishlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            wishlist.products.add(product)
            return Response({'message': 'Product added to wishlist'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Remove product from wishlist"""
        try:
            product_id = request.data.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            wishlist = get_object_or_404(Wishlist, user=request.user.profile)
            
            if product not in wishlist.products.all():
                return Response(
                    {'error': 'Product not in wishlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            wishlist.products.remove(product)
            return Response({'message': 'Product removed from wishlist'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CART VIEWS :::::
class AddToCartView(APIView):
    """Add product to cart"""
    def post(self, request, slug):
        try:
            product = get_object_or_404(Product, slug=slug, is_available=True)
            
            # Check stock availability
            if product.in_stock <= 0:
                return Response(
                    {'error': 'Product out of stock'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_id = request.session.get('cart_id', None)
            quantity = int(request.data.get('quantity', 1))
            size_id = request.data.get('size_id', None)
            
            with transaction.atomic():
                if cart_id:
                    cart = Cart.objects.filter(id=cart_id).first()
                    if cart is None:
                        cart = Cart.objects.create(total=0)
                        request.session['cart_id'] = cart.id
                else:
                    cart = Cart.objects.create(total=0)
                    request.session['cart_id'] = cart.id
                
                # Assign cart to user if authenticated
                if request.user.is_authenticated and hasattr(request.user, 'profile'):
                    cart.profile = request.user.profile
                    cart.save()
                
                # Get size if provided
                selected_size = None
                if size_id:
                    selected_size = ProductSize.objects.filter(id=size_id).first()
                
                # Check if product with same size already in cart
                cart_product = cart.items.filter(
                    product=product,
                    selected_size=selected_size
                ).first()
                
                if cart_product:
                    new_quantity = cart_product.quantity + quantity
                    
                    # Check stock
                    if new_quantity > product.in_stock:
                        return Response(
                            {'error': f'Only {product.in_stock} items available'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    cart_product.quantity = new_quantity
                    cart_product.save()
                    message = 'Item quantity updated in cart'
                else:
                    # Check stock
                    if quantity > product.in_stock:
                        return Response(
                            {'error': f'Only {product.in_stock} items available'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    cart_product = CartProduct.objects.create(
                        cart=cart,
                        product=product,
                        quantity=quantity,
                        selected_size=selected_size
                    )
                    message = 'Item added to cart'
                
                # Update cart total
                cart.update_total()
                
                serializer = CartSerializer(cart)
                return Response({
                    'message': message,
                    'cart': serializer.data
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MyCartView(APIView):
    """Get user cart"""
    def get(self, request):
        try:
            cart_id = request.session.get('cart_id', None)
            
            if not cart_id:
                return Response({
                    'cart': None,
                    'message': 'Cart is empty'
                }, status=status.HTTP_200_OK)
            
            cart = Cart.objects.filter(id=cart_id).first()
            
            if not cart:
                return Response({
                    'cart': None,
                    'message': 'Cart not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Assign cart to user if authenticated
            if request.user.is_authenticated and hasattr(request.user, 'profile'):
                if not cart.profile:
                    cart.profile = request.user.profile
                    cart.save()
            
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ManageCartView(APIView):
    """Manage cart items (increase, decrease, remove)"""
    def post(self, request, id):
        action = request.data.get('action')
        
        try:
            cart_product = get_object_or_404(CartProduct, id=id)
            cart = cart_product.cart
            product = cart_product.product
            
            if action == "inc":
                # Check stock
                if cart_product.quantity + 1 > product.in_stock:
                    return Response(
                        {'error': f'Only {product.in_stock} items available'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
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
            
            else:
                return Response(
                    {'error': 'Invalid action'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CHECKOUT VIEW :::::
class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        cart_id = request.session.get('cart_id', None)
        
        if not cart_id:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart = get_object_or_404(Cart, id=cart_id)
            
            # Check if cart is empty
            if not cart.items.exists():
                return Response(
                    {'error': 'Cart is empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate stock for all items
            for item in cart.items.all():
                if item.quantity > item.product.in_stock:
                    return Response(
                        {'error': f'Insufficient stock for {item.product.title}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            serializer = CheckoutSerializer(data=request.data)
            
            if serializer.is_valid():
                with transaction.atomic():
                    # Create order
                    order = serializer.save(
                        cart=cart,
                        user=request.user.profile,
                        amount=cart.total,
                        subtotal=cart.total,
                        order_status='pending'
                    )
                    
                    # Create order items
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
                        
                        # Update product stock
                        product = cart_item.product
                        product.in_stock -= cart_item.quantity
                        product.save()
                    
                    # Clear cart session
                    del request.session['cart_id']
                    
                    # Return payment URL if using Paystack
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

#::::: PAYMENT VIEW :::::
class PaymentPageView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            order = get_object_or_404(Order, id=id, user=request.user.profile)
            
            if order.payment_complete:
                return Response(
                    {'message': 'Payment already completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize Paystack payment
            url = "https://api.paystack.co/transaction/initialize"
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            data = {
                "amount": order.amount_value(),
                "email": order.email,
                "reference": order.ref
            }
            
            response = requests.post(url, headers=headers, json=data)
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
                return Response(
                    {'error': 'Payment initiation failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: VERIFY PAYMENT VIEW :::::
class VerifyPaymentView(APIView):
    def get(self, request, ref):
        try:
            order = get_object_or_404(Order, ref=ref)
            
            # Verify payment with Paystack
            url = f'https://api.paystack.co/transaction/verify/{ref}'
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            response = requests.get(url, headers=headers)
            response_data = response.json()
            
            if response_data.get("status") and response_data["data"]["status"] == "success":
                # Verify amount matches
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
                    return Response(
                        {'error': 'Payment amount mismatch'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            elif response_data["data"]["status"] == "abandoned":
                order.order_status = "pending"
                order.save()
                return Response(
                    {'error': 'Payment abandoned, please try again'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'error': 'Payment verification failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Order.DoesNotExist:
            return Response(
                {'error': 'Invalid payment reference'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: ORDER VIEWS :::::
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

#::::: HOMEPAGE SECTIONS VIEW :::::
class HomepageSectionsView(APIView):
    """Get all homepage sections"""
    def get(self, request):
        try:
            sections = HomepageSection.objects.filter(is_active=True).order_by('order')
            serializer = HomepageSectionSerializer(sections, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: CATEGORY GROUPS VIEW :::::
class CategoryGroupsView(APIView):
    """Get organized category groups with their products"""
    def get(self, request):
        try:
            # Get category type from query params
            category_type = request.query_params.get('type', None)
            
            if category_type:
                categories = Category.objects.filter(
                    category_type=category_type,
                    is_active=True
                )
            else:
                # Get all main category types
                categories = Category.objects.filter(
                    category_type__in=['gifts', 'fashion_finds', 'home_favourites'],
                    is_active=True
                )
            
            result = []
            for category in categories:
                # Get featured and top rated products
                all_products = category.get_all_products()
                featured = [p for p in all_products if p.is_featured][:10]
                top_rated = category.get_top_rated_products(limit=10)
                
                result.append({
                    'category': CategoryDetailSerializer(category).data,
                    'featured_products': ProductListSerializer(featured, many=True).data,
                    'top_rated_products': ProductListSerializer(top_rated, many=True).data,
                    'product_count': len(all_products)
                })
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: BRAND VIEW :::::
class BrandView(APIView):
    def get(self, request):
        try:
            brands = Brand.objects.filter(is_active=True)
            serializer = BrandSerializer(brands, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: TAG VIEW :::::
class TagView(APIView):
    def get(self, request):
        try:
            tags = Tag.objects.all()
            serializer = TagSerializer(tags, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: PRODUCT SIZE VIEW :::::
class ProductSizeView(APIView):
    def get(self, request):
        try:
            sizes = ProductSize.objects.all()
            
            # Filter by category if provided
            category = request.query_params.get('category', None)
            if category:
                sizes = sizes.filter(category=category)
            
            serializer = ProductSizeSerializer(sizes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add these views to the end of the file

#::::: GIFTS PAGE VIEWS :::::
class GiftsPageDataView(APIView):
    """Get all data needed for the gifts page"""
    def get(self, request):
        try:
            data = {}
            
            # Get all gift guide sections
            best_gift_guides = GiftGuideSection.objects.filter(
                section_type='best_gift_guides',
                is_active=True
            ).prefetch_related(
                Prefetch('gift_products', queryset=GiftGuideProduct.objects.select_related('product')),
                'featured_products',
                'categories'
            ).order_by('order')[:5]
            
            valentines_gifts = GiftGuideSection.objects.filter(
                section_type='valentines_gifts',
                is_active=True
            ).prefetch_related(
                Prefetch('gift_products', queryset=GiftGuideProduct.objects.select_related('product')),
                'featured_products'
            ).order_by('order')[:1]
            
            bestselling_gifts = GiftGuideSection.objects.filter(
                section_type='bestselling_gifts',
                is_active=True
            ).prefetch_related(
                Prefetch('gift_products', queryset=GiftGuideProduct.objects.select_related('product')),
                'featured_products'
            ).order_by('order')[:1]
            
            personalized_presents = GiftGuideSection.objects.filter(
                section_type='personalized_presents',
                is_active=True
            ).prefetch_related(
                Prefetch('gift_products', queryset=GiftGuideProduct.objects.select_related('product')),
                'featured_products'
            ).order_by('order')[:1]
            
            # Get gift categories
            gift_occasions = Category.objects.filter(
                category_type='gift_occasion',
                is_active=True
            ).order_by('order')[:8]
            
            gift_interests = Category.objects.filter(
                category_type='gift_interest',
                is_active=True
            ).order_by('order')[:8]
            
            gift_popular = Category.objects.filter(
                category_type='gift_popular',
                is_active=True
            ).order_by('order')[:8]
            
            # Get top rated gift products
            top_rated_products = Product.objects.filter(
                Q(category__category_type__in=['gifts', 'gift_occasion', 'gift_interest']) |
                Q(tags__name__icontains='gift'),
                is_available=True,
                in_stock__gt=0,
                rating__gte=4.0
            ).distinct().order_by('-rating', '-review_count')[:20]
            
            # Auto-populate sections if they're empty
            self._populate_section_if_empty(best_gift_guides, 'best_gift_guides')
            self._populate_section_if_empty(valentines_gifts, 'valentines_gifts')
            self._populate_section_if_empty(bestselling_gifts, 'bestselling_gifts')
            self._populate_section_if_empty(personalized_presents, 'personalized_presents')
            
            # Re-fetch after potential population
            best_gift_guides = GiftGuideSection.objects.filter(
                section_type='best_gift_guides',
                is_active=True
            ).prefetch_related('gift_products').order_by('order')[:5]
            
            data.update({
                'best_gift_guides': GiftGuideSectionSerializer(best_gift_guides, many=True).data,
                'valentines_gifts': GiftGuideSectionSerializer(valentines_gifts, many=True).data,
                'bestselling_gifts': GiftGuideSectionSerializer(bestselling_gifts, many=True).data,
                'personalized_presents': GiftGuideSectionSerializer(personalized_presents, many=True).data,
                'gift_occasions': CategoryListSerializer(gift_occasions, many=True).data,
                'gift_interests': CategoryListSerializer(gift_interests, many=True).data,
                'gift_popular': CategoryListSerializer(gift_popular, many=True).data,
                'top_rated_products': ProductListSerializer(top_rated_products, many=True).data,
                'page_title': "Etsy's Best Gift Guides",
                'page_description': "Discover curated picks for every person and moment, straight from extraordinary small shops."
            })
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch gifts page data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _populate_section_if_empty(self, sections, section_type):
        """Create default section if none exists"""
        if not sections.exists():
            if section_type == 'best_gift_guides':
                # Create Best Gift Guides section
                section = GiftGuideSection.objects.create(
                    title="Etsy's Best Gift Guides",
                    section_type=section_type,
                    description="Discover curated picks for every person and moment, straight from extraordinary small shops.",
                    guide_links=[
                        {"title": "Best of Valentine's Day", "url": "/gifts/valentines-day"},
                        {"title": "Top 100 Galentine's Picks", "url": "/gifts/galentines"},
                        {"title": "Birthday Gifts", "url": "/gifts/birthday"},
                        {"title": "Top 100 Aquarius Gifts", "url": "/gifts/aquarius"},
                        {"title": "Milestone Birthdays", "url": "/gifts/milestone"},
                        {"title": "Anniversary Gifts", "url": "/gifts/anniversary"},
                        {"title": "Engagement Gifts", "url": "/gifts/engagement"},
                        {"title": "Personalised Gifts", "url": "/gifts/personalized"},
                        {"title": "Gifts for Him", "url": "/gifts/him"},
                        {"title": "Gifts for Her", "url": "/gifts/her"},
                        {"title": "Gifts for Kids", "url": "/gifts/kids"},
                        {"title": "Gifts for Pets", "url": "/gifts/pets"}
                    ]
                )
            elif section_type == 'valentines_gifts':
                section = GiftGuideSection.objects.create(
                    title="Valentine's Day Gifts",
                    section_type=section_type,
                    description="Find the perfect Valentine's Day gift"
                )
            elif section_type == 'bestselling_gifts':
                section = GiftGuideSection.objects.create(
                    title="Best-selling gifts they'll love",
                    section_type=section_type,
                    description="Top picks based on customer reviews and sales"
                )
            elif section_type == 'personalized_presents':
                section = GiftGuideSection.objects.create(
                    title="Presents you can personalise",
                    section_type=section_type,
                    description="Customizable gifts for that personal touch"
                )

class GiftGuideSectionDetailView(APIView):
    """Get specific gift guide section with products"""
    def get(self, request, section_type):
        try:
            section = get_object_or_404(
                GiftGuideSection,
                section_type=section_type,
                is_active=True
            )
            
            # Get products for the section
            gift_products = section.gift_products.select_related('product').order_by('display_order')
            
            # If no custom products, use featured products
            if not gift_products.exists() and section.featured_products.exists():
                products = section.featured_products.filter(
                    is_available=True,
                    in_stock__gt=0
                ).select_related('category', 'brand')[:20]
            elif not gift_products.exists():
                # Auto-generate products based on section type
                if section_type == 'valentines_gifts':
                    products = Product.objects.filter(
                        Q(title__icontains='valentine') |
                        Q(description__icontains='valentine') |
                        Q(tags__name__icontains='valentine'),
                        is_available=True,
                        in_stock__gt=0
                    )[:20]
                elif section_type == 'bestselling_gifts':
                    products = Product.objects.filter(
                        is_bestseller=True,
                        is_available=True,
                        in_stock__gt=0
                    ).order_by('-rating', '-review_count')[:20]
                elif section_type == 'personalized_presents':
                    products = Product.objects.filter(
                        Q(title__icontains='personalized') |
                        Q(description__icontains='personalized') |
                        Q(tags__name__icontains='custom'),
                        is_available=True,
                        in_stock__gt=0
                    )[:20]
                else:
                    products = Product.objects.filter(
                        is_available=True,
                        in_stock__gt=0
                    ).order_by('-rating')[:20]
            else:
                products = [gp.product for gp in gift_products]
            
            return Response({
                'section': GiftGuideSectionSerializer(section).data,
                'products': ProductListSerializer(products, many=True).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: GIFT CATEGORY PRODUCTS VIEW :::::
class GiftCategoryProductsView(APIView):
    """Get products for specific gift category"""
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, category_slug):
        try:
            category = get_object_or_404(
                Category.objects.filter(
                    Q(category_type__in=['gifts', 'gift_occasion', 'gift_interest', 'gift_popular']) |
                    Q(title__icontains='gift'),
                    is_active=True
                ),
                slug=category_slug
            )
            
            # Get all products from this category and subcategories
            products = Product.objects.filter(
                Q(category=category) | Q(category__parent=category),
                is_available=True,
                in_stock__gt=0
            ).distinct()
            
            # Apply filters
            min_price = request.query_params.get('min_price', None)
            max_price = request.query_params.get('max_price', None)
            if min_price:
                products = products.filter(price__gte=min_price)
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
            
            # Pagination
            paginator = self.pagination_class()
            paginated_products = paginator.paginate_queryset(products, request)
            
            return Response({
                'category': CategoryDetailSerializer(category).data,
                'products': ProductListSerializer(paginated_products, many=True).data,
                'total_products': products.count()
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Add this view to the views.py file
class BestOfValentineView(APIView):
    """Get Best of Valentine's Day page data"""
    def get(self, request):
        try:
            # Get the Best of Valentine's Day section
            valentine_section = GiftGuideSection.objects.filter(
                section_type='best_of_valentine',
                is_active=True
            ).first()
            
            # If no section exists, create a default one
            if not valentine_section:
                valentine_section = GiftGuideSection.objects.create(
                    title="Best of Valentine's Day",
                    section_type='best_of_valentine',
                    description="Picks you'll love",
                    is_active=True
                )
            
            # Get categories for the sidebar
            valentine_categories = Category.objects.filter(
                Q(title__icontains='valentine') |
                Q(description__icontains='valentine') |
                Q(slug__icontains='valentine'),
                is_active=True
            ).distinct()[:10]
            
            # If no specific categories found, use default categories
            if not valentine_categories.exists():
                valentine_categories = Category.objects.filter(
                    is_active=True,
                    title__in=[
                        "Valentine's Day Cards",
                        "Valentine's Day Party Finds",
                        "Personalised Jewellery",
                        "Gifts for Him",
                        "Gifts for Her"
                    ]
                )[:10]
            
            # Get products with Valentine's tags or in Valentine's categories
            products = Product.objects.filter(
                Q(title__icontains='valentine') |
                Q(description__icontains='valentine') |
                Q(tags__name__icontains='valentine') |
                Q(category__title__icontains='valentine'),
                is_available=True,
                in_stock__gt=0
            ).distinct().select_related('category', 'brand')
            
            # Apply filters from request
            price_filter = request.query_params.get('price', 'any')
            if price_filter != 'any':
                if price_filter == 'under25':
                    products = products.filter(price__lt=25)
                elif price_filter == '25to50':
                    products = products.filter(price__gte=25, price__lte=50)
                elif price_filter == '50to100':
                    products = products.filter(price__gte=50, price__lte=100)
                elif price_filter == 'over100':
                    products = products.filter(price__gt=100)
            
            on_sale = request.query_params.get('on_sale', 'false') == 'true'
            if on_sale:
                products = products.filter(discount_price__isnull=False)
            
            etsy_picks = request.query_params.get('etsy_picks', 'false') == 'true'
            if etsy_picks:
                # Get products marked as Etsy's Picks in GiftGuideProduct
                etsy_pick_products = GiftGuideProduct.objects.filter(
                    etsy_pick=True,
                    product__in=products
                ).values_list('product_id', flat=True)
                products = products.filter(id__in=etsy_pick_products)
            
            # Sort products
            sort_by = request.query_params.get('sort', '-rating')
            if sort_by == 'price':
                products = products.order_by('price')
            elif sort_by == '-price':
                products = products.order_by('-price')
            elif sort_by == 'low_to_high':
                products = products.order_by('price')
            elif sort_by == 'high_to_low':
                products = products.order_by('-price')
            else:
                products = products.order_by('-rating', '-review_count')
            
            # Prepare products data with shop info
            products_data = []
            for product in products[:20]:
                # Get shop name
                shop_name = None
                if product.seller and product.seller.user:
                    shop_name = product.seller.user.username
                
                # Check if product is Etsy's Pick
                gift_product = GiftGuideProduct.objects.filter(
                    product=product,
                    gift_section=valentine_section,
                    etsy_pick=True
                ).first()
                
                etsy_pick = gift_product.etsy_pick if gift_product else False
                
                products_data.append({
                    'id': product.id,
                    'title': product.title,
                    'slug': product.slug,
                    'short_description': product.short_description,
                    'price': float(product.price),
                    'discount_price': float(product.discount_price) if product.discount_price else None,
                    'discount_percentage': product.discount_percentage,
                    'final_price': float(product.final_price),
                    'main': product.main.url if product.main else None,
                    'rating': float(product.rating),
                    'review_count': product.review_count,
                    'is_featured': product.is_featured,
                    'is_bestseller': product.is_bestseller,
                    'is_deal': product.is_deal,
                    'is_new_arrival': product.is_new_arrival,
                    'condition': product.condition,
                    'shop_name': shop_name,
                    'etsy_pick': etsy_pick,
                    'free_delivery': random.choice([True, False]),  # This would come from shipping info in a real app
                    'has_video': random.choice([True, False]),  # This would come from media in a real app
                })
            
            # Related searches
            related_searches = [
                "custom embroidered sage green bows",
                "ceramic pot mug",
                "lucky is to have you",
                "valentines day cards",
                "classroom",
                "family portrait",
                "love lounge"
            ]
            
            response_data = {
                'section': {
                    'id': valentine_section.id,
                    'title': valentine_section.title,
                    'description': valentine_section.description,
                    'section_type': valentine_section.section_type,
                },
                'categories': CategoryListSerializer(valentine_categories, many=True).data,
                'products': products_data,
                'related_searches': related_searches,
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
                        {'value': 'AU', 'label': 'Australia'},
                        {'value': 'CA', 'label': 'Canada'},
                        {'value': 'FR', 'label': 'France'},
                    ]
                },
                'current_filters': {
                    'price': price_filter,
                    'on_sale': on_sale,
                    'etsy_picks': etsy_picks,
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch Best of Valentine\'s Day data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ::::: HOME FAVOURITES VIEWS :::::
class HomeFavouritesView(APIView):
    """Get Home Favourites page data"""
    def get(self, request):
        try:
            # Get Home Favourites section
            home_favourites_section = HomepageSection.objects.filter(
                section_type='home_favourites',
                is_active=True
            ).first()
            
            # If no section exists, create a default one
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
                
                for i, title in enumerate(default_home_categories):
                    category = Category.objects.create(
                        title=title,
                        slug=slugify(title),
                        category_type='home_favourites',
                        image=f'categories/home/{slugify(title)}.jpg',
                        order=i,
                        is_active=True
                    )
                    home_categories = Category.objects.filter(category_type='home_favourites')
            
            # Get products for Home Favourites sections
            # Spring-ready linens products
            spring_linens_products = Product.objects.filter(
                Q(title__icontains='linen') |
                Q(description__icontains='linen') |
                Q(category__title__icontains='linen'),
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
                    "images": self._get_shop_images(["ceramic", "vintage", "macrame", "crochet"])
                },
                {
                    "name": "BrooxFurniture",
                    "rating": 5,
                    "reviewCount": "116",
                    "images": self._get_shop_images(["watch", "pillow", "linen", "vintage"])
                },
                {
                    "name": "ForestlandLinen",
                    "rating": 5,
                    "reviewCount": "4,977",
                    "images": self._get_shop_images(["crochet", "linen", "pillow", "macrame"])
                },
                {
                    "name": "MDTMobilier",
                    "rating": 3,
                    "reviewCount": "70",
                    "images": self._get_shop_images(["vintage", "watch", "ceramic", "vintage"])
                }
            ]
            
            # Discover more categories
            discover_categories = [
                {
                    "title": "Special Starts on Etsy",
                    "image": self._get_category_image("special"),
                    "slug": "special-starts"
                },
                {
                    "title": "Global Seller Spotlight",
                    "image": self._get_category_image("global"),
                    "slug": "global-seller"
                },
                {
                    "title": "Vintage Home Decor",
                    "image": self._get_category_image("vintage"),
                    "slug": "vintage-home-decor"
                },
                {
                    "title": "Explore Unique Wall Art",
                    "image": self._get_category_image("wall-art"),
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
                "hero_categories": [
                    {
                        "title": "Home Decor",
                        "image": self._get_category_image("home-decor"),
                        "slug": "home-decor"
                    },
                    {
                        "title": "Kitchen & Dining",
                        "image": self._get_category_image("kitchen"),
                        "slug": "kitchen-dining"
                    },
                    {
                        "title": "Furniture",
                        "image": self._get_category_image("furniture"),
                        "slug": "furniture"
                    },
                    {
                        "title": "Vintage Rugs",
                        "image": self._get_category_image("rugs"),
                        "slug": "vintage-rugs"
                    },
                    {
                        "title": "Lighting",
                        "image": self._get_category_image("lighting"),
                        "slug": "lighting"
                    },
                    {
                        "title": "Bedding",
                        "image": self._get_category_image("bedding"),
                        "slug": "bedding"
                    }
                ],
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
                        {"value": "over100", "label": "Over USD 100"},
                        {"value": "custom", "label": "Custom"}
                    ]
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch Home Favourites data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_shop_images(self, keywords):
        """Get product images for shop display"""
        images = []
        for keyword in keywords:
            product = Product.objects.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword),
                is_available=True,
                main__isnull=False
            ).first()
            if product:
                images.append(product.main.url)
            else:
                # Fallback to placeholder
                images.append("/media/categories/placeholder.jpg")
        return images
    
    def _get_category_image(self, category_name):
        """Get image for a category"""
        category = Category.objects.filter(
            title__icontains=category_name,
            image__isnull=False
        ).first()
        if category:
            return category.image.url
        return "/media/categories/placeholder.jpg"

#::::: FASHION FINDS VIEW :::::
class FashionFindsView(APIView):
    """Get all data needed for Fashion Finds page"""
    
    def get(self, request):
        try:
            # Get Fashion Finds section
            fashion_section = HomepageSection.objects.filter(
                section_type='fashion_finds',
                is_active=True
            ).first()
            
            # If no section exists, create a default one
            if not fashion_section:
                fashion_section = HomepageSection.objects.create(
                    title="Fashion Finds",
                    section_type='fashion_finds',
                    description="Discover fashion items from small shops",
                    is_active=True,
                    order=0
                )
            
            # Get Fashion Finds categories (hero section)
            fashion_categories = Category.objects.filter(
                Q(category_type='fashion_finds') |
                Q(parent_category__name__icontains='fashion') |
                Q(title__icontains='clothing') |
                Q(title__icontains='wear'),
                is_active=True
            ).distinct()[:12]
            
            # If no specific categories found, create/use default ones
            if not fashion_categories.exists():
                default_categories = [
                    "Women's Clothing",
                    "Men's Clothing", 
                    "Kids & Baby Clothing",
                    "Free Delivery: Cosy Knits",
                    "Personalised Tees & Sweatshirts",
                    "Jackets & Coats",
                    "Hats & Beanies",
                    "Handbags",
                    "Bag Charms & Keyrings",
                    "Hair Accessories",
                    "Lounge & Sleepwear",
                    "Travel Must-Haves"
                ]
                
                for i, title in enumerate(default_categories):
                    category, created = Category.objects.get_or_create(
                        title=title,
                        defaults={
                            'slug': slugify(title),
                            'category_type': 'fashion_finds',
                            'image': f'categories/fashion/{slugify(title)}.jpg',
                            'order': i,
                            'is_active': True
                        }
                    )
                fashion_categories = Category.objects.filter(
                    title__in=default_categories,
                    is_active=True
                ).order_by('order')[:12]
            
            # Get Fashion Shops We Love
            fashion_shops = FashionShop.objects.filter(
                is_featured=True
            ).prefetch_related('featured_products').order_by('order')[:4]
            
            # If no shops exist, create default ones
            if not fashion_shops.exists():
                default_shops = [
                    {
                        'name': 'SbriStudio',
                        'display_name': 'Sbristudio',
                        'rating': 5,
                        'review_count': 2841
                    },
                    {
                        'name': 'Plexida',
                        'display_name': 'Plexida',
                        'rating': 5,
                        'review_count': 2092
                    },
                    {
                        'name': 'GemBlue',
                        'display_name': 'GemBlue',
                        'rating': 5,
                        'review_count': 2473
                    },
                    {
                        'name': 'LetterParty',
                        'display_name': 'LetterParty',
                        'rating': 5,
                        'review_count': 273
                    }
                ]
                
                for i, shop_data in enumerate(default_shops):
                    shop = FashionShop.objects.create(
                        name=shop_data['name'],
                        slug=slugify(shop_data['name']),
                        display_name=shop_data['display_name'],
                        rating=shop_data['rating'],
                        review_count=shop_data['review_count'],
                        order=i,
                        is_featured=True
                    )
                    
                    # Add some random products to the shop
                    products = Product.objects.filter(
                        is_available=True,
                        in_stock__gt=0
                    ).order_by('?')[:4]
                    shop.featured_products.set(products)
                
                fashion_shops = FashionShop.objects.filter(is_featured=True).order_by('order')[:4]
            
            # Get products for different sections
            # Personalised clothes products
            personalised_clothes = Product.objects.filter(
                Q(title__icontains='personalised') |
                Q(title__icontains='custom') |
                Q(title__icontains='embroidered') |
                Q(description__icontains='personalised') |
                Q(tags__name__icontains='custom'),
                is_available=True,
                in_stock__gt=0
            ).distinct().order_by('-rating', '-review_count')[:20]
            
            # Unique handbags products
            unique_handbags = Product.objects.filter(
                Q(title__icontains='handbag') |
                Q(title__icontains='purse') |
                Q(title__icontains='tote') |
                Q(title__icontains='bag') |
                Q(category__title__icontains='bag'),
                is_available=True,
                in_stock__gt=0
            ).distinct().order_by('-rating', '-review_count')[:20]
            
            # Personalised jewellery products
            personalised_jewellery = Product.objects.filter(
                Q(title__icontains='jewellery') |
                Q(title__icontains='jewelry') |
                Q(title__icontains='necklace') |
                Q(title__icontains='ring') |
                Q(title__icontains='bracelet') |
                Q(category__title__icontains='jewellery'),
                is_available=True,
                in_stock__gt=0
            ).distinct().order_by('-rating', '-review_count')[:20]
            
            # Get Promo Cards
            promo_cards = FashionPromoCard.objects.filter(
                is_active=True
            ).order_by('order')[:2]
            
            # If no promo cards exist, create default ones
            if not promo_cards.exists():
                promo_cards_data = [
                    {
                        'title': 'Elevate your everyday jewellery',
                        'button_text': 'Shop now',
                        'button_url': '/jewellery'
                    },
                    {
                        'title': 'The Charm Shop',
                        'button_text': 'Shop now',
                        'button_url': '/charms'
                    }
                ]
                
                for i, card_data in enumerate(promo_cards_data):
                    FashionPromoCard.objects.create(
                        title=card_data['title'],
                        button_text=card_data['button_text'],
                        button_url=card_data['button_url'],
                        order=i,
                        is_active=True,
                        image=f'fashion_promo/card_{i+1}.jpg'
                    )
                
                promo_cards = FashionPromoCard.objects.filter(is_active=True).order_by('order')[:2]
            
            # Get Trending section
            trending = FashionTrending.objects.filter(
                is_active=True
            )[:1]
            
            # If no trending exists, create default
            if not trending.exists():
                FashionTrending.objects.create(
                    title="Trending now: Burgundy hues",
                    description="Jump into one of our favourite colours for winter. The deep shade will bring a moody vibe to any outfit as we move into chillier temperatures.",
                    button_text="Try it out",
                    button_url="/trending/burgundy",
                    is_active=True,
                    image='fashion_trending/burgundy.jpg'
                )
                trending = FashionTrending.objects.filter(is_active=True)[:1]
            
            # Get Discover More section
            discover_more = FashionDiscover.objects.filter(
                is_active=True
            ).order_by('order')[:4]
            
            # If no discover more exists, create default
            if not discover_more.exists():
                discover_data = [
                    {'title': 'Special Starts on Etsy', 'url': '/special-starts'},
                    {'title': 'The Linen Shop', 'url': '/linen-shop'},
                    {'title': 'The Personalisation Shop', 'url': '/personalisation-shop'},
                    {'title': "Etsy's Guide to Vintage", 'url': '/vintage-guide'}
                ]
                
                for i, item in enumerate(discover_data):
                    FashionDiscover.objects.create(
                        title=item['title'],
                        url=item['url'],
                        order=i,
                        is_active=True,
                        image=f'fashion_discover/discover_{i+1}.jpg'
                    )
                
                discover_more = FashionDiscover.objects.filter(is_active=True).order_by('order')[:4]
            
            # Prepare response data
            response_data = {
                'hero_title': fashion_section.title,
                'hero_description': fashion_section.description,
                'hero_categories': CategoryListSerializer(fashion_categories, many=True).data,
                'shops_we_love': FashionShopSerializer(fashion_shops, many=True).data,
                'personalised_clothes_products': ProductListSerializer(personalised_clothes, many=True).data,
                'unique_handbags_products': ProductListSerializer(unique_handbags, many=True).data,
                'personalised_jewellery_products': ProductListSerializer(personalised_jewellery, many=True).data,
                'promo_cards': FashionPromoCardSerializer(promo_cards, many=True).data,
                'trending': FashionTrendingSerializer(trending, many=True).data,
                'discover_more': FashionDiscoverSerializer(discover_more, many=True).data,
                'filters': {
                    'price_options': [
                        {'value': 'any', 'label': 'Any price'},
                        {'value': 'under25', 'label': 'Under USD 25'},
                        {'value': '25to50', 'label': 'USD 25 to USD 50'},
                        {'value': '50to100', 'label': 'USD 50 to USD 100'},
                        {'value': 'over100', 'label': 'Over USD 100'},
                        {'value': 'custom', 'label': 'Custom'}
                    ]
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch Fashion Finds data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#::::: GIFT FINDER VIEWS :::::

class GiftFinderDataView(APIView):
    """Get all data for the Gift Finder page"""
    
    def get(self, request):
        try:
            # Get all active gift occasions
            hero_occasions = GiftOccasion.objects.filter(is_active=True).order_by('order')
            
            # Get all active gift interests
            browse_interests = GiftInterest.objects.filter(is_active=True).order_by('order')
            
            # Get featured collections
            featured_collections = GiftCollection.objects.filter(
                is_active=True
            ).prefetch_related(
                Prefetch('collection_products', queryset=GiftCollectionProduct.objects.select_related('product')),
                'persona'
            ).order_by('order')[:2]
            
            # Get all recipients with their items
            recipients = GiftRecipient.objects.filter(
                is_active=True
            ).prefetch_related(
                Prefetch('items', queryset=GiftRecipientItem.objects.filter(is_active=True).order_by('order'))
            ).order_by('order')[:2]
            
            # Get gift personas for Get Inspired section
            gift_personas = GiftPersona.objects.filter(
                persona_type='interest',
                is_active=True
            ).order_by('order')[:10]
            
            # Get guilty pleasures
            guilty_pleasures = GiftPersona.objects.filter(
                persona_type='guilty_pleasure',
                is_active=True
            ).order_by('order')[:5]
            
            # Get zodiac signs
            zodiac_signs = GiftPersona.objects.filter(
                persona_type='zodiac_sign',
                is_active=True
            ).order_by('order')[:5]
            
            # Get gift grid items
            gift_grid_items = GiftGridItem.objects.filter(is_active=True).order_by('order')[:8]
            
            # Get popular gift categories
            popular_categories = PopularGiftCategory.objects.filter(is_active=True).order_by('order')
            
            # If no data exists, populate with default data
            self._populate_default_data_if_empty()
            
            # Re-fetch after potential population
            hero_occasions = GiftOccasion.objects.filter(is_active=True).order_by('order')
            browse_interests = GiftInterest.objects.filter(is_active=True).order_by('order')
            featured_collections = GiftCollection.objects.filter(is_active=True).order_by('order')[:2]
            recipients = GiftRecipient.objects.filter(is_active=True).order_by('order')[:2]
            gift_personas = GiftPersona.objects.filter(persona_type='interest', is_active=True).order_by('order')[:10]
            guilty_pleasures = GiftPersona.objects.filter(persona_type='guilty_pleasure', is_active=True).order_by('order')[:5]
            zodiac_signs = GiftPersona.objects.filter(persona_type='zodiac_sign', is_active=True).order_by('order')[:5]
            gift_grid_items = GiftGridItem.objects.filter(is_active=True).order_by('order')[:8]
            popular_categories = PopularGiftCategory.objects.filter(is_active=True).order_by('order')
            
            response_data = {
                'hero_occasions': GiftOccasionSerializer(hero_occasions, many=True).data,
                'browse_interests': GiftInterestSerializer(browse_interests, many=True).data,
                'featured_collections': GiftCollectionSerializer(featured_collections, many=True).data,
                'recipients': GiftRecipientSerializer(recipients, many=True).data,
                'gift_personas': GiftPersonaSerializer(gift_personas, many=True).data,
                'guilty_pleasures': GiftPersonaSerializer(guilty_pleasures, many=True).data,
                'zodiac_signs': GiftPersonaSerializer(zodiac_signs, many=True).data,
                'gift_grid_items': GiftGridItemSerializer(gift_grid_items, many=True).data,
                'popular_gift_categories': PopularGiftCategorySerializer(popular_categories, many=True).data,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch Gift Finder data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _populate_default_data_if_empty(self):
        """Populate default data if no records exist"""
        
        # Populate Gift Occasions
        if not GiftOccasion.objects.exists():
            occasions = [
                {'label': "Valentine's Day", 'date': "14 Feb", 'icon': 'Heart', 'slug': 'valentines-day', 'order': 1},
                {'label': "Easter", 'date': "05 Apr", 'icon': 'Egg', 'slug': 'easter', 'order': 2},
                {'label': "Lunar New Year", 'date': "17 Feb", 'icon': 'Moon', 'slug': 'lunar-new-year', 'order': 3},
                {'label': "Eid", 'date': "20 Mar", 'icon': 'Star', 'slug': 'eid', 'order': 4},
                {'label': "Wedding", 'icon': 'Cake', 'slug': 'wedding', 'order': 5},
                {'label': "Birthday", 'icon': 'Cake', 'slug': 'birthday', 'order': 6},
                {'label': "Anniversary", 'icon': 'CircleDot', 'slug': 'anniversary', 'order': 7},
                {'label': "Thank You", 'icon': 'Mail', 'slug': 'thank-you', 'order': 8},
                {'label': "Sympathy", 'icon': 'Flower', 'slug': 'sympathy', 'order': 9},
                {'label': "Get Well", 'icon': 'SmilePlus', 'slug': 'get-well', 'order': 10},
                {'label': "Engagement", 'icon': 'Gift', 'slug': 'engagement', 'order': 11},
            ]
            for occasion in occasions:
                GiftOccasion.objects.create(**occasion)
        
        # Populate Gift Interests
        if not GiftInterest.objects.exists():
            interests = [
                "Jewellery", "Beer, Wine & Cocktails", "Crafting", "Nature", "Useful Gifts",
                "Music", "Collectibles", "Films", "Science", "Family", "Pets",
                "Health & Fitness", "Tech", "Astrology", "Cooking & Baking", "Reading", "Sports",
            ]
            for i, interest in enumerate(interests):
                GiftInterest.objects.create(name=interest, order=i)
        
        # Populate Gift Personas for collections
        if not GiftPersona.objects.filter(persona_type='collection').exists():
            vegetarian = GiftPersona.objects.create(
                name="The Vegetarian",
                persona_type='collection',
                bg_color="bg-green-50",
                accent_color="bg-green-600",
                order=1
            )
            
            jewellery_lover = GiftPersona.objects.create(
                name="The Jewellery Lover",
                persona_type='collection',
                bg_color="bg-purple-50",
                accent_color="bg-purple-600",
                order=2
            )
            
            # Create collections for these personas
            veg_collection = GiftCollection.objects.create(
                persona=vegetarian,
                title="Vegetable Earrings",
                interest_tag="Jewellery",
                order=1
            )
            
            jewellery_collection = GiftCollection.objects.create(
                persona=jewellery_lover,
                title="Resin Statement Necklaces",
                interest_tag="Jewellery",
                order=2
            )
        
        # Populate Gift Recipients
        if not GiftRecipient.objects.exists():
            partner = GiftRecipient.objects.create(
                label="For your Partner",
                icon="Heart",
                slug="for-your-partner",
                order=1
            )
            
            parent = GiftRecipient.objects.create(
                label="For your Parent",
                icon="Users",
                slug="for-your-parent",
                order=2
            )
            
            # Add items for Partner
            partner_items = [
                "Gemstone Rings", "Self Care Gift Boxes", "Handmade Candles",
                "Birthstone Jewellery", "Handmade Leather Bracelets", "Date Ideas"
            ]
            for i, item in enumerate(partner_items):
                GiftRecipientItem.objects.create(
                    recipient=partner,
                    title=item,
                    order=i
                )
            
            # Add items for Parent
            parent_items = [
                "Desk Organisers and Trays", "Monogram Washbags", "Handmade Leather Keyrings",
                "Handmade Bath Products", "Birthstone Rings", "Spa Gift Sets"
            ]
            for i, item in enumerate(parent_items):
                GiftRecipientItem.objects.create(
                    recipient=parent,
                    title=item,
                    order=i
                )
        
        # Populate other recipients
        other_recipients = [
            {"label": "Kids", "icon": "Baby", "slug": "kids"},
            {"label": "Coworker", "icon": "Briefcase", "slug": "coworker"},
            {"label": "Sibling", "icon": "Users", "slug": "sibling"},
            {"label": "Friend", "icon": "UserPlus", "slug": "friend"},
            {"label": "Teacher", "icon": "GraduationCap", "slug": "teacher"},
            {"label": "Grandparent", "icon": "User", "slug": "grandparent"},
        ]
        for recipient in other_recipients:
            GiftRecipient.objects.get_or_create(
                label=recipient["label"],
                defaults={
                    "icon": recipient["icon"],
                    "slug": recipient["slug"],
                    "order": 10
                }
            )
        
        # Populate Gift Personas for Get Inspired
        if not GiftPersona.objects.filter(persona_type='interest').exists():
            personas = [
                {"name": "Gadget Obsessed", "bg_color": "bg-sky-200", "accent_color": "bg-orange-500"},
                {"name": "Adventurer", "bg_color": "bg-sky-200", "accent_color": "bg-orange-500"},
                {"name": "K-pop Stan", "bg_color": "bg-green-500", "accent_color": "bg-yellow-400"},
                {"name": "Music Lover", "bg_color": "bg-blue-600", "accent_color": "bg-blue-300"},
                {"name": "Science Buff", "bg_color": "bg-orange-400", "accent_color": "bg-sky-200"},
                {"name": "Fisherman", "bg_color": "bg-orange-400", "accent_color": "bg-sky-200"},
                {"name": "Renaissance Faire Fan", "bg_color": "bg-yellow-400", "accent_color": "bg-purple-300"},
                {"name": "Crafter", "bg_color": "bg-green-800", "accent_color": "bg-yellow-400"},
                {"name": "Girlfriend", "bg_color": "bg-yellow-300", "accent_color": "bg-green-400"},
                {"name": "Coffee Connoisseur", "bg_color": "bg-green-500", "accent_color": "bg-green-300"},
            ]
            for i, persona in enumerate(personas):
                GiftPersona.objects.create(
                    name=persona["name"],
                    persona_type='interest',
                    bg_color=persona["bg_color"],
                    accent_color=persona["accent_color"],
                    order=i
                )
        
        # Populate Guilty Pleasures
        if not GiftPersona.objects.filter(persona_type='guilty_pleasure').exists():
            guilty = [
                {"name": "Alien Obsessed", "bg_color": "bg-yellow-400"},
                {"name": "Pasta Lover", "bg_color": "bg-yellow-400"},
                {"name": "Karaoke Crooner", "bg_color": "bg-green-800"},
                {"name": "Chocoholic", "bg_color": "bg-green-500"},
                {"name": "Anime Fan", "bg_color": "bg-green-500"},
            ]
            for i, persona in enumerate(guilty):
                GiftPersona.objects.create(
                    name=persona["name"],
                    persona_type='guilty_pleasure',
                    bg_color=persona["bg_color"],
                    order=i
                )
        
        # Populate Zodiac Signs
        if not GiftPersona.objects.filter(persona_type='zodiac_sign').exists():
            zodiac = [
                {"name": "Aquarius", "bg_color": "bg-green-500"},
                {"name": "Astrology Expert", "bg_color": "bg-yellow-300"},
                {"name": "Scorpio", "bg_color": "bg-orange-500"},
                {"name": "Taurus", "bg_color": "bg-sky-200"},
                {"name": "Gemini", "bg_color": "bg-orange-400"},
            ]
            for i, persona in enumerate(zodiac):
                GiftPersona.objects.create(
                    name=persona["name"],
                    persona_type='zodiac_sign',
                    bg_color=persona["bg_color"],
                    order=i
                )
        
        # Populate Gift Grid Items
        if not GiftGridItem.objects.exists():
            grid_items = [
                {"title": "Date Night Ideas", "size": "small", "order": 1},
                {"title": '"Reasons I Love You" Gifts', "size": "large", "order": 2},
                {"title": "Forever Flowers", "size": "small", "order": 3},
                {"title": "Valentine's Day Cards", "size": "small", "order": 4},
                {"title": "Pocket Hugs", "size": "small", "order": 5},
                {"title": "Where We Met Gifts", "size": "large", "order": 6},
                {"title": "Artisanal Chocolate Boxes", "size": "small", "order": 7},
                {"title": "Pressed Flower Gifts", "size": "small", "order": 8},
            ]
            for item in grid_items:
                GiftGridItem.objects.create(**item)
        
        # Populate Popular Gift Categories
        if not PopularGiftCategory.objects.exists():
            categories = ["Jewellery", "Clothing", "Home Decor", "Accessories", "Pet Gifts"]
            for i, cat in enumerate(categories):
                PopularGiftCategory.objects.create(name=cat, order=i)

class GiftCollectionByInterestView(APIView):
    """Get gift collections filtered by interest"""
    
    def get(self, request):
        interest = request.query_params.get('interest', 'Jewellery')
        
        try:
            collections = GiftCollection.objects.filter(
                interest_tag=interest,
                is_active=True
            ).prefetch_related(
                Prefetch('collection_products', queryset=GiftCollectionProduct.objects.select_related('product')),
                'persona'
            ).order_by('order')[:2]
            
            # If no collections found for this interest, return default ones
            if not collections.exists():
                collections = GiftCollection.objects.filter(is_active=True).order_by('order')[:2]
            
            serializer = GiftCollectionSerializer(collections, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PopularGiftsByCategoryView(APIView):
    """Get popular gifts filtered by category"""
    
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        category = request.query_params.get('category', 'Jewellery')
        
        try:
            products = Product.objects.filter(
                Q(category__title__icontains=category) |
                Q(title__icontains=category) |
                Q(tags__name__icontains=category),
                is_available=True,
                in_stock__gt=0
            ).distinct().order_by('-rating', '-review_count')[:8]
            
            # If no products found, return random popular products
            if not products.exists():
                products = Product.objects.filter(
                    is_available=True,
                    in_stock__gt=0
                ).order_by('-rating', '-review_count')[:8]
            
            serializer = ProductListSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)