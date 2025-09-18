from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryView.as_view(), name='category-list'),  # ← Use class-based view
    path('category/<str:pk>/', views.CategoryEditView.as_view(), name='category-detail'),
    path('products/', views.ProductView.as_view(), name='product-list'),
    path('product/<str:pk>/', views.ProductEditView.as_view(), name='product-detail'),
    path('addtocart/<str:id>/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('mycart/', views.MyCartView.as_view(), name='my-cart'),
    path('managecart/<str:id>/', views.ManageCart.as_view(), name='manage-cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('payment/<str:id>/', views.PaymentPageView.as_view(), name='payment'),
    path('verify/<str:ref>/', views.VerifyPaymentView.as_view(), name='verify-payment'),
]