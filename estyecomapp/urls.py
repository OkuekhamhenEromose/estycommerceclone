from django.urls import path
from . import views

urlpatterns = [
    # Homepage Data
    path('homepage/', views.SimpleHomepageView.as_view(), name='homepage-data'),
    # path('homepage/', views.HomepageDataView.as_view(), name='homepage-data'),
    path('homepage/component/', views.ComponentSpecificDataView.as_view(), name='homepage-component'),
    path('homepage/section/<str:section_type>/', views.HomepageSectionProductsView.as_view(), name='homepage-section'),

    # Parent Categories
    path('parent-categories/', views.ParentCategoryView.as_view(), name='parent-categories'),
    
    # Categories
    path('categories/', views.CategoryView.as_view(), name='category-list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('category/<slug:slug>/products/', views.CategoryProductsView.as_view(), name='category-products'),
    
    # Category Groups (Gifts, Fashion Finds, Home Favourites)
    path('category-groups/', views.CategoryGroupsView.as_view(), name='category-groups'),
    
    # Navigation
    path('navigation/', views.NavigationView.as_view(), name='navigation'),
    
    # Top 100 Gifts
    path('top-100-gifts/', views.Top100GiftsView.as_view(), name='top-100-gifts'),
    
    # Products
    path('products/', views.ProductView.as_view(), name='product-list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/upload/', views.ProductUploadView.as_view(), name='product-upload'),
    path('products/update/<int:product_id>/', views.ProductUploadView.as_view(), name='product-update'),
    
    # Product Reviews
    path('product/<slug:product_slug>/reviews/', views.ProductReviewView.as_view(), name='product-reviews'),
    
    # Brands
    path('brands/', views.BrandView.as_view(), name='brand-list'),
    
    # Tags
    path('tags/', views.TagView.as_view(), name='tag-list'),
    
    # Product Sizes
    path('product-sizes/', views.ProductSizeView.as_view(), name='product-sizes'),
    
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
    # path('homepage/', views.HomepageDataView, name='homepage'),
    path('homepage-sections/', views.HomepageSectionsView.as_view(), name='homepage-sections'),
    path('gifts-page/', views.GiftsPageDataView.as_view(), name='gifts-page'),
    path('gifts-section/<str:section_type>/', views.GiftGuideSectionDetailView.as_view(), name='gift-guide-section'),
    path('gift-category/<slug:category_slug>/products/', views.GiftCategoryProductsView.as_view(), name='gift-category-products'),
    path('best-of-valentine/', views.BestOfValentineView.as_view(), name='best-of-valentine'),
    path('home-favourites/', views.HomeFavouritesView.as_view(), name='home-favourites'),
    path('fashion-finds/', views.FashionFindsView.as_view(), name='fashion-finds'),
    # Gift Finder endpoints
    path('gift-finder/', views.GiftFinderDataView.as_view(), name='gift-finder'),
    path('gift-finder/collections/', views.GiftCollectionByInterestView.as_view(), name='gift-collections'),
    path('gift-finder/popular-gifts/', views.PopularGiftsByCategoryView.as_view(), name='popular-gifts'),
    path('gift-teaser/', views.GiftTeaserDataView.as_view(), name='gift-teaser'),
    path('gift-teaser/mark-as-gift/', views.MarkOrderAsGiftView.as_view(), name='mark-as-gift'),
    path('accessories/categories/', views.AccessoriesCategoryView.as_view(), name='accessories-categories'),
    path('accessories/products/', views.AccessoriesProductsView.as_view(), name='accessories-products'),
    path('accessories/category/<slug:category_slug>/', views.AccessoriesProductsView.as_view(), name='accessories-category-products'),
    path('accessories/filters/', views.AccessoriesFiltersView.as_view(), name='accessories-filters'),
    path("art-collectibles/categories/",    views.ArtCategoryView.as_view(),  name="art-categories"),
    path("art-collectibles/products/",      views.ArtProductsView.as_view(),  name="art-products"),
    path("art-collectibles/category/<slug:category_slug>/", views.ArtProductsView.as_view(), name="art-category-products"),
    path("art-collectibles/filters/",       views.ArtFiltersView.as_view(),   name="art-filters"),
    path("baby/categories/",                         views.BabyCategoryView.as_view(),  name="baby-categories"),
    path("baby/products/",                           views.BabyProductsView.as_view(),  name="baby-products"),
    path("baby/category/<slug:category_slug>/",      views.BabyProductsView.as_view(),  name="baby-category-products"),
    path("baby/filters/",                            views.BabyFiltersView.as_view(),   name="baby-filters"),
]