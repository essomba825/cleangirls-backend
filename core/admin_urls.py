# -*- coding: utf-8 -*-
"""
CleanGirls E-Commerce Admin & Management Routing
Django URL patterns for all administrative API endpoints.
Mounted under: /api/v1/admin/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_views import (
    AdminAuthLoginView, AdminAuthLogoutView, AdminDashboardStatsView,
    AdminCategoryViewSet, AdminCosmeticProductViewSet, AdminClothingProductViewSet,
    AdminOrderViewSet, AdminPaymentTransactionViewSet, AdminCustomerViewSet,
    AdminFacebookConfigView, AdminExchangeRatesView, AdminDemoDataManagementView,
    AdminNotificationView
)

router = DefaultRouter()
router.register('categories', AdminCategoryViewSet, basename='admin-category')
router.register('cosmetics', AdminCosmeticProductViewSet, basename='admin-cosmetic')
router.register('clothes', AdminClothingProductViewSet, basename='admin-clothing')
router.register('orders', AdminOrderViewSet, basename='admin-order')
router.register('payments', AdminPaymentTransactionViewSet, basename='admin-payment')

urlpatterns = [
    # Authentification Admin (login/logout via Django authenticate)
    path('auth/login/', AdminAuthLoginView.as_view(), name='admin-auth-login'),
    path('auth/logout/', AdminAuthLogoutView.as_view(), name='admin-auth-logout'),

    # Tableau de bord et statistiques
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),

    # Endpoints Router (Catégories, Cosmétiques, Mode, Commandes, Paiements)
    path('', include(router.urls)),

    # Clients et Profils consolidés
    path('customers/', AdminCustomerViewSet.as_view(), name='admin-customers'),

    # Configurations système
    path('config/facebook/', AdminFacebookConfigView.as_view(), name='admin-config-facebook'),
    path('config/exchange-rates/', AdminExchangeRatesView.as_view(), name='admin-config-exchange-rates'),

    # Gestion des données de démonstration
    path('demo-data/', AdminDemoDataManagementView.as_view(), name='admin-demo-data'),

    # Notifications personnalisées (WebPush)
    path('notifications/vapid_public_key/', AdminNotificationView.as_view(), name='admin-notif-vapid'),
    path('notifications/send_custom/', AdminNotificationView.as_view(), name='admin-notif-send'),
]
