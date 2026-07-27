from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, CosmeticProduct, ClothingProduct, UserProfile,
    GuestSession, Order, OrderItem, PaymentTransaction, FavoriteItem, FacebookConfig
)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class CosmeticProductSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.slug')
    categoryLabel = serializers.CharField(source='category.name')
    priceFCFA = serializers.IntegerField(source='price_fcfa')
    image = serializers.SerializerMethodField()
    isNew = serializers.BooleanField(source='is_new')
    videoUrl = serializers.SerializerMethodField()

    class Meta:
        model = CosmeticProduct
        fields = ['id', 'name', 'category', 'categoryLabel', 'description', 'priceFCFA', 'image', 'videoUrl', 'isNew', 'rating']

    def get_id(self, obj):
        return f"cos-{obj.id}"

    def get_image(self, obj):
        """Fichier uploadé prioritaire, sinon URL CDN."""
        request = self.context.get('request')
        if obj.image_file:
            url = obj.image_file.url
            return request.build_absolute_uri(url) if request else url
        return obj.image_url or ''

    def get_videoUrl(self, obj):
        request = self.context.get('request')
        if obj.video_file:
            url = obj.video_file.url
            return request.build_absolute_uri(url) if request else url
        return ''


class ClothingProductSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.slug')
    categoryLabel = serializers.CharField(source='category.name')
    priceFCFA = serializers.IntegerField(source='price_fcfa')
    image = serializers.SerializerMethodField()
    isNew = serializers.BooleanField(source='is_new')
    sizes = serializers.SerializerMethodField()
    videoUrl = serializers.SerializerMethodField()

    class Meta:
        model = ClothingProduct
        fields = ['id', 'name', 'category', 'categoryLabel', 'description', 'priceFCFA', 'image', 'videoUrl', 'isNew', 'sizes']

    def get_id(self, obj):
        return f"clt-{obj.id}"

    def get_image(self, obj):
        """Fichier uploadé prioritaire, sinon URL CDN."""
        request = self.context.get('request')
        if obj.image_file:
            url = obj.image_file.url
            return request.build_absolute_uri(url) if request else url
        return obj.image_url or ''

    def get_videoUrl(self, obj):
        request = self.context.get('request')
        if obj.video_file:
            url = obj.video_file.url
            return request.build_absolute_uri(url) if request else url
        return ''

    def get_sizes(self, obj):
        return [
            {"size": "XS", "stock": obj.stock_xs},
            {"size": "S", "stock": obj.stock_s},
            {"size": "M", "stock": obj.stock_m},
            {"size": "L", "stock": obj.stock_l},
            {"size": "XL", "stock": obj.stock_xl},
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    firstName = serializers.CharField(source='user.first_name')
    email = serializers.EmailField(source='user.email', required=False, allow_blank=True)
    isSubscribed = serializers.BooleanField(source='receive_newsletters')
    avatarUrl = serializers.SerializerMethodField()
    phone = serializers.CharField(source='phone_number')

    class Meta:
        model = UserProfile
        fields = ['username', 'firstName', 'email', 'isSubscribed', 'avatarUrl', 'phone']

    def get_avatarUrl(self, obj):
        first_name = obj.user.first_name or obj.user.username or 'CG'
        return f"https://api.dicebear.com/7.x/initials/svg?seed={first_name}&backgroundColor=ff8da1,70a1ff"


class OrderItemSerializer(serializers.ModelSerializer):
    productId = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    priceFCFA = serializers.IntegerField(source='price_fcfa')
    image = serializers.SerializerMethodField()
    selectedSize = serializers.CharField(source='selected_size', required=False, allow_blank=True)
    type = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['productId', 'name', 'priceFCFA', 'image', 'quantity', 'selectedSize', 'type']

    def get_productId(self, obj):
        if obj.cosmetic_product:
            return f"cos-{obj.cosmetic_product.id}"
        elif obj.clothing_product:
            return f"clt-{obj.clothing_product.id}"
        return None

    def get_name(self, obj):
        if obj.cosmetic_product:
            return obj.cosmetic_product.name
        elif obj.clothing_product:
            return obj.clothing_product.name
        return "Produit inconnu"

    def get_image(self, obj):
        """Fichier uploadé prioritaire, sinon URL CDN."""
        request = self.context.get('request')
        product = obj.cosmetic_product or obj.clothing_product
        if not product:
            return ''
        if product.image_file:
            url = product.image_file.url
            return request.build_absolute_uri(url) if request else url
        return product.image_url or ''

    def get_type(self, obj):
        if obj.cosmetic_product:
            return "cosmetic"
        elif obj.clothing_product:
            return "clothing"
        return ""


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    date = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='total_amount_fcfa')
    operator = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'date', 'amount', 'operator', 'phone', 'items', 'status']

    def get_date(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')

    def get_operator(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.operator
        return 'N/A'

    def get_phone(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.phone_debited
        elif obj.user and hasattr(obj.user, 'profile') and obj.user.profile.phone_number:
            return obj.user.profile.phone_number
        elif obj.guest:
            return obj.guest.phone_number
        return ''


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'
