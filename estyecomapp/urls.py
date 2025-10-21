from django.urls import path
from . import views

urlpatterns = [
    # Parent Categories
    path('parent-categories/', views.ParentCategoryView.as_view(), name='parent-categories'),
    
    # Categories
    path('categories/', views.CategoryView.as_view(), name='category-list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Navigation
    path('navigation/', views.NavigationView.as_view(), name='navigation'),
    
    # Products
    path('products/', views.ProductView.as_view(), name='product-list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Product Reviews
    path('product/<slug:product_slug>/reviews/', views.ProductReviewView.as_view(), name='product-reviews'),
    
    # Brands
    path('brands/', views.BrandView.as_view(), name='brand-list'),
    
    # Tags
    path('tags/', views.TagView.as_view(), name='tag-list'),
    
    # Wishlist
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    
    # Cart
    path('add-to-cart/<slug:slug>/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('my-cart/', views.MyCartView.as_view(), name='my-cart'),
    path('manage-cart/<int:id>/', views.ManageCartView.as_view(), name='manage-cart'),
    
    # Checkout
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    
    # Payment
    path('payment/<int:id>/', views.PaymentPageView.as_view(), name='payment'),
    path('verify-payment/<str:ref>/', views.VerifyPaymentView.as_view(), name='verify-payment'),
    
    # Orders
    path('my-orders/', views.MyOrdersView.as_view(), name='my-orders'),
    path('order/<str:order_number>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Homepage Sections
    path('homepage-sections/', views.HomepageSectionsView.as_view(), name='homepage-sections'),
]