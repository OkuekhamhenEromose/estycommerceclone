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
        
class BestOfValentineView(APIView):
    """Get Best of Valentine's Day curated collection"""
    def get(self, request):
        try:
            # Try to get the existing section
            valentine_section = GiftGuideSection.objects.filter(
                section_type='best_of_valentine',
                is_active=True
            ).first()
            
            # If no section exists, create a default one
            if not valentine_section:
                valentine_section = GiftGuideSection.objects.create(
                    title="Best of Valentine's Day",
                    section_type='best_of_valentine',
                    description="Picks you'll love for Valentine's Day",
                    is_active=True
                )
            
            # Get filter parameters from request
            price_filter = request.query_params.get('price', None)
            on_sale = request.query_params.get('on_sale', None) == 'true'
            etsy_picks = request.query_params.get('etsy_picks', None) == 'true'
            sent_from = request.query_params.get('sent_from', None)
            
            # Base query for Valentine's Day products
            products = Product.objects.filter(
                Q(title__icontains='valentine') |
                Q(description__icontains='valentine') |
                Q(tags__name__icontains='valentine') |
                Q(category__title__icontains='valentine'),
                is_available=True,
                in_stock__gt=0
            ).distinct()
            
            # Apply price filters
            if price_filter:
                if price_filter == 'under_25':
                    products = products.filter(price__lt=25)
                elif price_filter == '25_to_50':
                    products = products.filter(price__gte=25, price__lte=50)
                elif price_filter == '50_to_100':
                    products = products.filter(price__gte=50, price__lte=100)
                elif price_filter == 'over_100':
                    products = products.filter(price__gt=100)
            
            # Apply sale filter
            if on_sale:
                products = products.filter(discount_price__isnull=False)
            
            # Sort options
            sort_by = request.query_params.get('sort', None)
            if sort_by == 'price_low_to_high':
                products = products.order_by('price')
            elif sort_by == 'price_high_to_low':
                products = products.order_by('-price')
            elif sort_by == 'rating':
                products = products.order_by('-rating', '-review_count')
            else:
                products = products.order_by('-rating', '-review_count')
            
            # Get the categories for the sidebar
            valentine_categories = Category.objects.filter(
                Q(title__icontains='valentine') |
                Q(description__icontains='valentine'),
                is_active=True
            ).distinct()[:10]
            
            # If no specific categories found, use generic Valentine's categories
            if not valentine_categories.exists():
                valentine_categories = Category.objects.filter(
                    title__in=[
                        "Valentine's Day Cards",
                        "Valentine's Day Party Finds",
                        "Personalised Jewellery",
                        "Valentine's Gifts for Him",
                        "Valentine's Gifts for Her"
                    ],
                    is_active=True
                )[:10]
            
            # Get related searches
            related_searches = [
                "custom embroidered sage green bows",
                "ceramic pot mug",
                "lucky is to have you",
                "valentines day cards",
                "classroom",
                "family portrait",
                "love lounge"
            ]
            
            # Create gift products if section is empty
            if not valentine_section.gift_products.exists():
                # Add some featured products to the section
                featured_products = products[:20]
                for idx, product in enumerate(featured_products):
                    GiftGuideProduct.objects.get_or_create(
                        gift_section=valentine_section,
                        product=product,
                        defaults={
                            'display_order': idx,
                            'etsy_pick': random.choice([True, False]),  # Randomly mark as Etsy's Pick
                            'shop_name': product.seller.user.username if product.seller else "Unknown Shop",
                            'badge_text': "Free delivery" if random.choice([True, False]) else None
                        }
                    )
            
            # Get section products with their metadata
            section_products = valentine_section.gift_products.select_related(
                'product'
            ).order_by('display_order')
            
            # If no section products, use the filtered products
            if not section_products.exists():
                products_list = products[:20]
                section_products_data = ProductListSerializer(products_list, many=True).data
            else:
                products_list = [gp.product for gp in section_products]
                section_products_data = []
                for gp in section_products:
                    product_data = ProductListSerializer(gp.product).data
                    product_data['etsy_pick'] = gp.etsy_pick
                    product_data['shop_name'] = gp.shop_name
                    product_data['badge_text'] = gp.badge_text
                    product_data['custom_title'] = gp.custom_title
                    section_products_data.append(product_data)
            
            response_data = {
                'section': {
                    'id': valentine_section.id,
                    'title': valentine_section.title,
                    'description': valentine_section.description,
                    'section_type': valentine_section.section_type,
                    'section_type_display': valentine_section.get_section_type_display(),
                },
                'categories': CategoryListSerializer(valentine_categories, many=True).data,
                'products': section_products_data,
                'filters': {
                    'price_options': [
                        {'value': 'any', 'label': 'Any price'},
                        {'value': 'under_25', 'label': 'Under $25'},
                        {'value': '25_to_50', 'label': '$25 to $50'},
                        {'value': '50_to_100', 'label': '$50 to $100'},
                        {'value': 'over_100', 'label': 'Over $100'},
                        {'value': 'custom', 'label': 'Custom'}
                    ],
                    'sort_options': [
                        {'value': 'relevance', 'label': 'Relevance'},
                        {'value': 'price_low_to_high', 'label': 'Price: Low to High'},
                        {'value': 'price_high_to_low', 'label': 'Price: High to Low'},
                        {'value': 'rating', 'label': 'Top Rated'}
                    ],
                    'shipping_options': [
                        {'value': 'anywhere', 'label': 'Anywhere'},
                        {'value': 'US', 'label': 'United States'},
                        {'value': 'UK', 'label': 'United Kingdom'},
                        {'value': 'AU', 'label': 'Australia'},
                        {'value': 'CA', 'label': 'Canada'},
                        {'value': 'EU', 'label': 'European Union'}
                    ]
                },
                'related_searches': related_searches,
                'total_products': len(products_list),
                'current_filters': {
                    'price': price_filter,
                    'on_sale': on_sale,
                    'etsy_picks': etsy_picks,
                    'sent_from': sent_from,
                    'sort': sort_by
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return Response({
                'error': str(e),
                'detail': error_detail,
                'message': 'Failed to fetch Valentine\'s Day data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)