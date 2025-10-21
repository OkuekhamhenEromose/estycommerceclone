from rest_framework import status, permissions, filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from django.shortcuts import reverse, get_object_or_404
from django.db import transaction
from django.db.models import Q, Avg, Count
from django.conf import settings

import requests
from .serializers import *
from .models import *

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
            }
            
            serializer = NavigationSerializer(data)
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
                'rating', '-rating', 'created', '-created'
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
                
                # Check if product already in cart
                cart_product = cart.items.filter(product=product).first()
                
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
                        quantity=quantity
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
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            product_name=cart_item.product.title,
                            product_price=cart_item.product.final_price,
                            quantity=cart_item.quantity,
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