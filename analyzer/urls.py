from django.urls import path
from .views import (
    ProductListView, ProductDetailView, ProductInsightsView,
    ScrapingView, ProcessProductsView
)

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<uuid:uuid>/', ProductDetailView.as_view(), name='product-detail'),
    path('insights/', ProductInsightsView.as_view(), name='product-insights'),
    path('scrape/', ScrapingView.as_view(), name='scrape-products'),
    path('process/', ProcessProductsView.as_view(), name='process-products'),
] 