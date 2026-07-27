from django.contrib import admin
from .models import (
    Category, CosmeticProduct, ClothingProduct, UserProfile,
    GuestSession, Order, OrderItem, PaymentTransaction, FavoriteItem, FacebookConfig
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'store_type')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('store_type',)
    search_fields = ('name',)


@admin.register(CosmeticProduct)
class CosmeticProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price_fcfa', 'is_new', 'rating', 'stock_quantity')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category', 'is_new')
    search_fields = ('name', 'description')


@admin.register(ClothingProduct)
class ClothingProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price_fcfa', 'is_new', 'stock_xs', 'stock_s', 'stock_m', 'stock_l', 'stock_xl')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category', 'is_new')
    search_fields = ('name', 'description')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'receive_newsletters', 'loyalty_points')
    search_fields = ('user__username', 'user__first_name', 'phone_number')
    list_filter = ('receive_newsletters',)


@admin.register(GuestSession)
class GuestSessionAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'phone_number', 'email', 'created_at')
    search_fields = ('first_name', 'phone_number', 'email')
    readonly_fields = ('created_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('cosmetic_product', 'clothing_product', 'selected_size', 'quantity', 'price_fcfa')


class PaymentTransactionInline(admin.StackedInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ('operator', 'payment_mode', 'amount_fcfa', 'phone_debited', 'ussd_string_dialed', 'transaction_id')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer_name', 'total_amount_fcfa', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'user__first_name', 'guest__first_name', 'delivery_address')
    inlines = [OrderItemInline, PaymentTransactionInline]
    readonly_fields = ('created_at',)

    def buyer_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name or obj.user.username} (Membre)"
        elif obj.guest:
            return f"{obj.guest.first_name} (Invitée)"
        return "Inconnu"
    buyer_name.short_description = "Acheteur"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'operator', 'amount_fcfa', 'is_verified', 'verified_at')
    list_filter = ('operator', 'is_verified', 'verified_at')
    search_fields = ('transaction_id', 'phone_debited')
    readonly_fields = ('order', 'operator', 'payment_mode', 'amount_fcfa', 'phone_debited', 'ussd_string_dialed', 'transaction_id')

    def save_model(self, request, obj, form, change):
        # Mettre à jour la date de validation automatique si is_verified passe à True
        if obj.is_verified and not obj.verified_at:
            from django.utils import timezone
            obj.verified_at = timezone.now()
            # Mettre à jour également le statut de la commande associée en PAID (si ce n'est pas déjà fait)
            if obj.order.status == 'PENDING':
                obj.order.status = 'PAID'
                obj.order.save()
        super().save_model(request, obj, form, change)


@admin.register(FavoriteItem)
class FavoriteItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'cosmetic_product', 'clothing_product', 'added_at')
    readonly_fields = ('added_at',)


@admin.register(FacebookConfig)
class FacebookConfigAdmin(admin.ModelAdmin):
    list_display = ('page_id', 'cache_ttl_minutes')
