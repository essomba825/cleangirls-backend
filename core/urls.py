from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExchangeRatesView, CosmeticProductViewSet, ClothingProductViewSet,
    LoginView, RegisterView, OrderViewSet, FavoriteViewSet, FacebookPostsView,
    WebpushSubscriptionStatusView
)

router = DefaultRouter()
router.register('cosmetics', CosmeticProductViewSet, basename='cosmetic')
router.register('clothes', ClothingProductViewSet, basename='clothing')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('config/exchange-rates/', ExchangeRatesView.as_view(), name='exchange-rates'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('facebook/posts/', FacebookPostsView.as_view(), name='facebook-posts'),
    path('favorites/toggle/', FavoriteViewSet.as_view({'post': 'create'}), name='favorites-toggle'),
    path('favorites/', FavoriteViewSet.as_view({'get': 'list'}), name='favorites-list'),
    path('webpush/check_status/', WebpushSubscriptionStatusView.as_view(), name='webpush-check-status'),
]
