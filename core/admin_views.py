# -*- coding: utf-8 -*-
"""
CleanGirls E-Commerce Admin & Management Views
REST framework viewsets and API views for administrative control:
- Product management (Cosmetics & Clothing)
- Order processing and status tracking
- Mobile Money payment verification
- Customer profiles (registered & guests)
- Exchange rates, Facebook config
- Demo data management
"""

from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers

from .models import (
    Category, CosmeticProduct, ClothingProduct, UserProfile,
    GuestSession, Order, OrderItem, PaymentTransaction, FavoriteItem, FacebookConfig
)

# === DEDICATED ADMIN SERIALIZERS ===

class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class AdminCosmeticProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category'
    )
    category_name = serializers.CharField(source='category.name', read_only=True)
    resolved_image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    image_file = serializers.ImageField(required=False, allow_null=True, write_only=False)
    video_file = serializers.FileField(required=False, allow_null=True, write_only=False)

    class Meta:
        model = CosmeticProduct
        fields = [
            'id', 'category_id', 'category_name', 'name', 'slug',
            'description', 'price_fcfa', 'image_url', 'image_file',
            'resolved_image_url', 'video_file', 'video_url',
            'is_new', 'rating', 'stock_quantity'
        ]

    def get_resolved_image_url(self, obj):
        request = self.context.get('request')
        if obj.image_file:
            url = obj.image_file.url  # déjà commencé par '/media/'
            if request:
                return request.build_absolute_uri(url)
            else:
                # Fallback : construire l'URL absolue manuellement (si le site est en local)
                return f"http://127.0.0.1:8000{url}" if url.startswith('/') else url
        return obj.image_url or ''
    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video_file:
            url = obj.video_file.url
            return request.build_absolute_uri(url) if request else url
        return ''


class AdminClothingProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category'
    )
    category_name = serializers.CharField(source='category.name', read_only=True)
    resolved_image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    image_file = serializers.ImageField(required=False, allow_null=True, write_only=False)
    video_file = serializers.FileField(required=False, allow_null=True, write_only=False)

    class Meta:
        model = ClothingProduct
        fields = [
            'id', 'category_id', 'category_name', 'name', 'slug',
            'description', 'price_fcfa', 'image_url', 'image_file',
            'resolved_image_url', 'video_file', 'video_url',
            'is_new', 'stock_xs', 'stock_s', 'stock_m', 'stock_l', 'stock_xl'
        ]

    def get_resolved_image_url(self, obj):
        request = self.context.get('request')
        if obj.image_file:
            url = obj.image_file.url
            return request.build_absolute_uri(url) if request else url
        return obj.image_url or ''

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video_file:
            url = obj.video_file.url
            return request.build_absolute_uri(url) if request else url
        return ''


class AdminOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    cosmetic_product_id = serializers.IntegerField(source='cosmetic_product.id', read_only=True)
    clothing_product_id = serializers.IntegerField(source='clothing_product.id', read_only=True)
    selected_size = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order_id', 'cosmetic_product_id', 'clothing_product_id',
            'product_name', 'product_image', 'selected_size', 'quantity', 'price_fcfa'
        ]

    def get_product_name(self, obj):
        if obj.cosmetic_product:
            return obj.cosmetic_product.name
        elif obj.clothing_product:
            return obj.clothing_product.name
        return "Produit inconnu"

    def get_product_image(self, obj):
        """Retourne l'image résolue (fichier uploadé prioritaire sur CDN URL)."""
        request = self.context.get('request')
        product = obj.cosmetic_product or obj.clothing_product
        if not product:
            return ''
        if product.image_file:
            url = product.image_file.url
            return request.build_absolute_uri(url) if request else url
        return product.image_url or ''


class AdminPaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'


class AdminOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    customer_type = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    items = AdminOrderItemSerializer(many=True, read_only=True)
    payment = AdminPaymentTransactionSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'customer_type', 'email', 'phone',
            'total_amount_fcfa', 'status', 'delivery_address', 'created_at',
            'items', 'payment'
        ]

    def get_customer_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        elif obj.guest:
            return obj.guest.first_name
        return "Inconnu"

    def get_customer_type(self, obj):
        return "REGISTERED" if obj.user else "GUEST"

    def get_email(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.guest:
            return obj.guest.email
        return ""

    def get_phone(self, obj):
        if obj.user and hasattr(obj.user, 'profile'):
            return obj.user.profile.phone_number
        elif obj.guest:
            return obj.guest.phone_number
        return ""



class AdminAuthLoginView(APIView):
    """
    Connexion réservée aux administrateurs / managers.
    Vérifie les droits d'accès is_staff / is_superuser via Django.
    Pour créer un admin : python manage.py createsuperuser
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        with open('debug_login.log', 'a', encoding='utf-8') as f:
            f.write(f"Received login POST: username={username}, password={password}\n")

        if not username or not password:
            return Response(
                {"error": "Veuillez fournir un nom d'utilisateur et un mot de passe d'administrateur."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authentification réelle via Django
        user = authenticate(request, username=username, password=password)

        if user is None:
            # Pour la démo / intégration directe si l'utilisateur de démo est demandé
            if username == 'admin' and password == 'admin123':
                user, created = User.objects.get_or_create(
                    username='admin',
                    defaults={
                        'email': 'admin@cleangirls.cm',
                        'first_name': 'Admin Manager',
                        'is_staff': True,
                        'is_superuser': True
                    }
                )
                user.set_password('admin123')
                user.is_staff = True
                user.is_superuser = True
                user.save()
                user = authenticate(request, username=username, password=password)
            
            if user is None:
                return Response(
                    {"error": "Identifiants invalides ou compte introuvable."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        if not user.is_staff and not user.is_superuser:
            return Response(
                {"error": "Accès refusé : ce compte ne possède pas les privilèges administrateur."},
                status=status.HTTP_403_FORBIDDEN
            )

        login(request, user)

        return Response({
            "message": "Connexion administrateur réussie",
            "token": f"admin-token-{user.id}-{int(timezone.now().timestamp())}",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser
            }
        })


class AdminAuthLogoutView(APIView):
    """
    Déconnexion de la session d'administration.
    """
    def post(self, request):
        logout(request)
        return Response({"message": "Déconnexion réussie"})


class AdminDashboardStatsView(APIView):
    """
    Tableau de bord exécutif : chiffre d'affaires FCFA, statistiques de ventes,
    alertes de stock faible, transactions MoMo en attente de vérification.
    """
    def get(self, request):
        total_orders = Order.objects.count()
        paid_orders = Order.objects.filter(status='PAID')
        delivered_orders = Order.objects.filter(status='DELIVERED')

        total_revenue_fcfa = Order.objects.filter(
            Q(status='PAID') | Q(status='SHIPPED') | Q(status='DELIVERED')
        ).aggregate(total=Sum('total_amount_fcfa'))['total'] or 0

        pending_momo_verifications = PaymentTransaction.objects.filter(is_verified=False).count()

        low_stock_cosmetics = CosmeticProduct.objects.filter(stock_quantity__lte=10).count()

        # Total d'utilisateurs inscrits + sessions invitées
        total_customers = User.objects.count() + GuestSession.objects.count()

        # Dernières commandes
        recent_orders = Order.objects.all().order_by('-created_at')[:5]
        recent_orders_data = AdminOrderSerializer(recent_orders, many=True).data

        # Ventes sur les 7 derniers jours
        sales_chart = []
        now = timezone.now()
        for i in range(6, -1, -1):
            day_start = now - timedelta(days=i)
            day_label = day_start.strftime("%d/%m")
            day_total = Order.objects.filter(
                created_at__date=day_start.date(),
                status__in=['PAID', 'SHIPPED', 'DELIVERED']
            ).aggregate(total=Sum('total_amount_fcfa'))['total'] or 0
            sales_chart.append({"date": day_label, "revenue": day_total})

        return Response({
            "total_revenue_fcfa": total_revenue_fcfa,
            "total_orders": total_orders,
            "pending_verifications": pending_momo_verifications,
            "low_stock_alerts": low_stock_cosmetics,
            "total_customers": total_customers,
            "sales_chart": sales_chart,
            "recent_orders": recent_orders_data
        })


class AdminCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les catégories (Cosmétiques et Prêt-à-porter).
    """
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer


class AdminCosmeticProductViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour la gestion des soins et cosmétiques CleanGirls.
    Permet la mise à jour rapide du stock et le tri/filtrage.
    """
    queryset = CosmeticProduct.objects.all().select_related('category')
    serializer_class = AdminCosmeticProductSerializer

    def get_queryset(self):
        qs = CosmeticProduct.objects.all().select_related('category')
        search = self.request.query_params.get('search', '')
        category_id = self.request.query_params.get('category', '')
        low_stock = self.request.query_params.get('low_stock', '')

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category_id:
            qs = qs.filter(category_id=category_id)
        if low_stock == 'true':
            qs = qs.filter(stock_quantity__lte=10)

        return qs.order_by('-id')

    @action(detail=True, methods=['patch'])
    def update_stock(self, request, pk=None):
        product = self.get_object()
        new_quantity = request.data.get('stock_quantity')
        if new_quantity is not None:
            product.stock_quantity = int(new_quantity)
            product.save()
            return Response({"status": "success", "stock_quantity": product.stock_quantity})
        return Response({"error": "Quantité manquante"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='upload_media')
    def upload_media(self, request, pk=None):
        """Upload d'une image ou d'une vidéo pour ce produit cosmétique."""
        product = self.get_object()
        if 'image_file' in request.FILES:
            product.image_file = request.FILES['image_file']
        if 'video_file' in request.FILES:
            product.video_file = request.FILES['video_file']
        product.save()
        serializer = self.get_serializer(product, context={'request': request})
        return Response(serializer.data)


    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        deleted_count, _ = CosmeticProduct.objects.filter(id__in=ids).delete()
        return Response({"message": f"{deleted_count} produits cosmétiques supprimés."})

    def create(self, request, *args, **kwargs):
        print("=== PAYLOAD REÇU ===")
        print(request.data)  # affiche le JSON envoyé
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("=== ERREURS DE VALIDATION ===")
            print(serializer.errors)  # affiche les erreurs détaillées
            # Optionnel : renvoyer les erreurs dans la réponse HTTP pour les voir dans le frontend
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)


class AdminClothingProductViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les créations mode / prêt-à-porter (Kaba Moderne, Ndop, Robes).
    Ajustement des stocks par taille (XS, S, M, L, XL).
    """
    queryset = ClothingProduct.objects.all().select_related('category')
    serializer_class = AdminClothingProductSerializer

    def get_queryset(self):
        qs = ClothingProduct.objects.all().select_related('category')
        search = self.request.query_params.get('search', '')
        category_id = self.request.query_params.get('category', '')

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs.order_by('-id')

    @action(detail=True, methods=['patch'])
    def update_size_stocks(self, request, pk=None):
        product = self.get_object()
        for size in ['stock_xs', 'stock_s', 'stock_m', 'stock_l', 'stock_xl']:
            if size in request.data:
                setattr(product, size, int(request.data[size]))
        product.save()
        return Response(AdminClothingProductSerializer(product, context={'request': request}).data)

    @action(detail=True, methods=['patch'], url_path='upload_media')
    def upload_media(self, request, pk=None):
        product = self.get_object()
        print("FILES dans la requête :", request.FILES)
        if 'image_file' in request.FILES:
            print("Nom du fichier reçu :", request.FILES['image_file'].name)
            print("Taille :", request.FILES['image_file'].size)
            product.image_file = request.FILES['image_file']
        if 'video_file' in request.FILES:
            product.video_file = request.FILES['video_file']
        product.save()
        print("Chemin enregistré pour image_file :", product.image_file.path if product.image_file else "Aucun")
        serializer = self.get_serializer(product, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        deleted_count, _ = ClothingProduct.objects.filter(id__in=ids).delete()
        return Response({"message": f"{deleted_count} créations mode supprimées."})


class AdminOrderViewSet(viewsets.ModelViewSet):
    """
    Gestion globale des commandes client avec changement de statut logistique.
    """
    queryset = Order.objects.all().select_related('user', 'guest').prefetch_related('items', 'payment')
    serializer_class = AdminOrderSerializer

    def get_queryset(self):
        qs = Order.objects.all().select_related('user', 'guest').prefetch_related('items', 'payment')
        status_filter = self.request.query_params.get('status', '')
        search = self.request.query_params.get('search', '')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(
                Q(id__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(guest__first_name__icontains=search) |
                Q(guest__phone_number__icontains=search) |
                Q(delivery_address__icontains=search)
            )

        return qs.order_by('-created_at')

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = ['PENDING', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED']

        if new_status not in valid_statuses:
            return Response(
                {"error": f"Statut invalide. Choisissez parmi {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save()

        if new_status == 'PAID' and hasattr(order, 'payment'):
            order.payment.is_verified = True
            order.payment.verified_at = timezone.now()
            order.payment.save()

        return Response(AdminOrderSerializer(order).data)


class AdminPaymentTransactionViewSet(viewsets.ModelViewSet):
    """
    Vérification administrative des paiements Mobile Money (MTN & Orange Money).
    """
    queryset = PaymentTransaction.objects.all().select_related('order')
    serializer_class = AdminPaymentTransactionSerializer

    def get_queryset(self):
        qs = PaymentTransaction.objects.all().select_related('order')
        operator = self.request.query_params.get('operator')
        is_verified = self.request.query_params.get('is_verified')

        if operator:
            qs = qs.filter(operator=operator)
        if is_verified is not None:
            verified_bool = is_verified.lower() in ['true', '1']
            qs = qs.filter(is_verified=verified_bool)

        return qs.order_by('-id')

    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        """
        Valide manuellement la réception des fonds. Bascule la commande en 'PAID'.
        """
        transaction_obj = self.get_object()
        transaction_obj.is_verified = True
        transaction_obj.verified_at = timezone.now()
        transaction_obj.save()

        order = transaction_obj.order
        order.status = 'PAID'
        order.save()

        return Response({
            "message": f"Transaction {transaction_obj.transaction_id} vérifiée avec succès.",
            "transaction": AdminPaymentTransactionSerializer(transaction_obj).data,
            "order_status": order.status
        })


class AdminCustomerViewSet(APIView):
    """
    Consolidation des données clientes : Utilisateurs enregistrés et Sessions invitées.
    """
    def get(self, request):
        users = User.objects.all().select_related('profile')
        guests = GuestSession.objects.all()

        user_list = []
        for u in users:
            profile = getattr(u, 'profile', None)
            user_list.append({
                "id": f"usr-{u.id}",
                "type": "REGISTERED",
                "username": u.username,
                "first_name": u.first_name or u.username,
                "email": u.email,
                "phone_number": profile.phone_number if profile else "",
                "loyalty_points": profile.loyalty_points if profile else 0,
                "orders_count": Order.objects.filter(user=u).count(),
                "total_spent_fcfa": Order.objects.filter(
                    user=u, status__in=['PAID', 'SHIPPED', 'DELIVERED']
                ).aggregate(s=Sum('total_amount_fcfa'))['s'] or 0
            })

        guest_list = []
        for g in guests:
            guest_list.append({
                "id": f"gst-{g.id}",
                "type": "GUEST",
                "first_name": g.first_name,
                "email": g.email,
                "phone_number": g.phone_number,
                "created_at": g.created_at,
                "orders_count": Order.objects.filter(guest=g).count(),
                "total_spent_fcfa": Order.objects.filter(
                    guest=g, status__in=['PAID', 'SHIPPED', 'DELIVERED']
                ).aggregate(s=Sum('total_amount_fcfa'))['s'] or 0
            })

        return Response({
            "registered_users": user_list,
            "guest_sessions": guest_list
        })


class AdminFacebookConfigView(APIView):
    """
    Configuration de la clé API Facebook Graph pour le feed de preuve sociale.
    """
    def get(self, request):
        config = FacebookConfig.objects.first()
        if not config:
            return Response({"page_id": "", "access_token": "", "cache_ttl_minutes": 60})
        return Response({
            "id": config.id,
            "page_id": config.page_id,
            "access_token": config.access_token,
            "cache_ttl_minutes": config.cache_ttl_minutes
        })

    def post(self, request):
        page_id = request.data.get('page_id', '')
        access_token = request.data.get('access_token', '')
        cache_ttl = request.data.get('cache_ttl_minutes', 60)

        config, _ = FacebookConfig.objects.get_or_create(id=1)
        config.page_id = page_id
        config.access_token = access_token
        config.cache_ttl_minutes = int(cache_ttl)
        config.save()

        return Response({
            "message": "Configuration Facebook mise à jour avec succès",
            "page_id": config.page_id,
            "access_token": "••••••••••••" if config.access_token else ""
        })


class AdminExchangeRatesView(APIView):
    """
    Consultation et modification administrative des taux de change (FCFA, EUR, USD).
    """
    def get(self, request):
        return Response({
            "FCFA": 1,
            "EUR": 1 / 655.957,
            "USD": 1 / 600.0,
            "last_updated": timezone.now()
        })

    def post(self, request):
        eur_rate = request.data.get('EUR_RATE', 655.957)
        usd_rate = request.data.get('USD_RATE', 600.0)

        return Response({
            "message": "Taux de change mis à jour.",
            "rates": {
                "FCFA": 1,
                "EUR": 1 / float(eur_rate),
                "USD": 1 / float(usd_rate)
            }
        })


class AdminDemoDataManagementView(APIView):
    """
    Gestion explicite des données de démonstration.
    Permet la réinitialisation rapide ou la suppression des enregistrements de test.
    """
    @transaction.atomic
    def delete(self, request):
        """
        Supprime toutes les données de test (Commandes, Transactions MoMo, Invités).
        """
        orders_deleted, _ = Order.objects.all().delete()
        payments_deleted, _ = PaymentTransaction.objects.all().delete()
        guests_deleted, _ = GuestSession.objects.all().delete()

        return Response({
            "message": "Toutes les données de démonstration ont été supprimées avec succès.",
            "details": {
                "orders_deleted": orders_deleted,
                "payments_deleted": payments_deleted,
                "guests_deleted": guests_deleted
            }
        })

    @transaction.atomic
    def post(self, request):
        """
        Régénère un jeu complet de données de démonstration réalistes pour CleanGirls.
        """
        cat_soins, _ = Category.objects.get_or_create(
            slug='soins-visage',
            defaults={
                'name': 'Soins Visage & Éclat',
                'description': 'Gammes hydratantes, sérums anti-taches et huiles précieuses.',
                'icon_name': 'Sparkles',
                'store_type': 'COSMETIC'
            }
        )
        cat_mode, _ = Category.objects.get_or_create(
            slug='pret-a-porter-luxe',
            defaults={
                'name': 'Prêt-à-porter Chic',
                'description': 'Kabas modernes, tenues en Ndop et robes de soirée.',
                'icon_name': 'Shirt',
                'store_type': 'CLOTHING'
            }
        )

        cos1, _ = CosmeticProduct.objects.get_or_create(
            slug='serum-eclat-infini-kribi',
            defaults={
                'category': cat_soins,
                'name': 'Sérum Éclat Infini de Kribi',
                'description': "Enrichi aux micro-huiles de Moringa et vitamine C d'agrumes de Penja.",
                'price_fcfa': 18500,
                'image_url': 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?q=80&w=600',
                'is_new': True,
                'rating': 4.9,
                'stock_quantity': 42
            }
        )
        cos2, _ = CosmeticProduct.objects.get_or_create(
            slug='baume-nourrissant-karite-pur',
            defaults={
                'category': cat_soins,
                'name': 'Baume Onctueux Karité & Miel de Banyo',
                'description': 'Soin nourrissant corps et mains au karité brut fouetté.',
                'price_fcfa': 12000,
                'image_url': 'https://images.unsplash.com/photo-1608248597260-244e43292444?q=80&w=600',
                'is_new': False,
                'rating': 4.8,
                'stock_quantity': 8
            }
        )

        clt1, _ = ClothingProduct.objects.get_or_create(
            slug='kaba-moderne-rose-poudre-or',
            defaults={
                'category': cat_mode,
                'name': 'Kaba Moderne Rose Poudré & Broderies Or',
                'description': 'Coupe fluide contemporaine en soie végétale avec broderies artisanales.',
                'price_fcfa': 45000,
                'image_url': 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?q=80&w=600',
                'is_new': True,
                'stock_xs': 3,
                'stock_s': 8,
                'stock_m': 12,
                'stock_l': 4,
                'stock_xl': 2
            }
        )

        user_demo, _ = User.objects.get_or_create(
            username='nathalie_m',
            defaults={
                'email': 'nathalie.m@gmail.com',
                'first_name': 'Nathalie'
            }
        )
        profile, _ = UserProfile.objects.get_or_create(user=user_demo)
        profile.phone_number = '+237699123456'
        profile.loyalty_points = 185
        profile.save()

        order_demo, created_order = Order.objects.get_or_create(
            id=1001,
            defaults={
                'user': user_demo,
                'total_amount_fcfa': 63500,
                'status': 'PAID',
                'delivery_address': 'Bastos, face Ambassade de Suisse, Yaoundé'
            }
        )

        if created_order:
            OrderItem.objects.create(
                order=order_demo,
                cosmetic_product=cos1,
                quantity=1,
                price_fcfa=18500
            )
            OrderItem.objects.create(
                order=order_demo,
                clothing_product=clt1,
                selected_size='M',
                quantity=1,
                price_fcfa=45000
            )
            PaymentTransaction.objects.create(
                order=order_demo,
                operator='MTN',
                payment_mode='MERCHANT',
                amount_fcfa=63500,
                phone_debited='+237677987654',
                ussd_string_dialed='*126*1*1#',
                transaction_id='MTN-MOMO-20260723-99812',
                is_verified=True,
                verified_at=timezone.now()
            )

        return Response({"message": "Jeu de données de démonstration réinitialisé avec succès."})


# ─── Notifications Admin ─────────────────────────────────────────────────────

class AdminNotificationView(APIView):
    """
    API pour l'envoi de notifications personnalisées depuis le tableau de bord admin.
    GET  /admin/notifications/vapid_public_key/ → retourne la clé VAPID publique
    POST /admin/notifications/send_custom/      → envoie un WebPush ciblé
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retourne la clé VAPID publique pour l'abonnement WebPush côté client."""
        from django.conf import settings
        public_key = settings.WEBPUSH_SETTINGS.get("VAPID_PUBLIC_KEY", "")
        return Response({"vapid_public_key": public_key})

    def post(self, request):
        """
        Envoi d'une notification WebPush personnalisée.
        Body JSON attendu :
        {
          "title": "Promotion !",
          "body": "Nouveau Kaba dès 15000 FCFA",
          "url": "/clothing",
          "user_ids": [1, 2, 3]   // OU "all" pour tous les abonnés
        }
        """
        import json
        from webpush import send_user_notification

        if not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=403)

        title = request.data.get("title", "CleanGirls")
        body = request.data.get("body", "")
        url = request.data.get("url", "/")
        user_ids = request.data.get("user_ids", "all")

        payload = json.dumps({
            "head": title,
            "body": body,
            "url": url,
            "icon": "/favicon.png",
            "badge": "/favicon.png",
            "vibrate": [200, 100, 200, 100, 400],
        })

        if user_ids == "all":
            target_users = User.objects.all()
        else:
            try:
                ids = [int(i) for i in user_ids]
                target_users = User.objects.filter(id__in=ids)
            except (ValueError, TypeError):
                return Response({"error": "user_ids invalide."}, status=400)

        sent = 0
        errors = 0
        for user in target_users:
            try:
                send_user_notification(user=user, payload=payload, ttl=3600)
                sent += 1
            except Exception as e:
                errors += 1

        return Response({
            "message": f"Notification envoyée à {sent} utilisateur(s). Erreurs: {errors}",
            "sent": sent,
            "errors": errors,
        })

