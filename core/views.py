from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Category, CosmeticProduct, ClothingProduct, UserProfile,
    GuestSession, Order, OrderItem, PaymentTransaction, FavoriteItem, FacebookConfig
)
from .serializers import (
    CategorySerializer, CosmeticProductSerializer, ClothingProductSerializer,
    UserProfileSerializer, OrderSerializer, PaymentTransactionSerializer
)

class ExchangeRatesView(APIView):
    """
    Retourne les taux de change configurés.
    """
    def get(self, request):
        return Response({
            "FCFA": 1,
            "EUR": 1 / 655.957,
            "USD": 1 / 600.0
        })


class CosmeticProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CosmeticProduct.objects.all()
    serializer_class = CosmeticProductSerializer


class ClothingProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClothingProduct.objects.all()
    serializer_class = ClothingProductSerializer


class LoginView(APIView):
    """
    Connexion sans mot de passe / par username.
    """
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email', '')
        first_name = request.data.get('firstName', '')
        subscribe = request.data.get('isSubscribed', True)
        phone = request.data.get('phone', '')

        if not username:
            return Response({"error": "Le nom d'utilisateur est requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Chercher ou créer l'utilisateur
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': first_name or username}
        )

        if not created:
            if first_name:
                user.first_name = first_name
            if email:
                user.email = email
            user.save()

        # Chercher ou créer le profil utilisateur
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.receive_newsletters = subscribe
        if phone:
            profile.phone_number = phone
        profile.save()

        # Connecter l'utilisateur (Session Django)
        login(request, user)

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class RegisterView(APIView):
    """
    Inscription complète par username.
    """
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email', '')
        first_name = request.data.get('firstName')
        subscribe = request.data.get('isSubscribed', True)
        phone = request.data.get('phone', '')

        if not username or not first_name:
            return Response({"error": "Le nom d'utilisateur et le prénom sont requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Créer ou mettre à jour
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': first_name}
        )

        if not created:
            user.first_name = first_name
            if email:
                user.email = email
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.receive_newsletters = subscribe
        if phone:
            profile.phone_number = phone
        profile.save()

        login(request, user)

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        Filtre les commandes pour l'utilisateur connecté ou selon l'email/téléphone passé en paramètre.
        """
        queryset = Order.objects.all()
        
        # 1. Par session connectée
        if self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)

        # 2. Par paramètre de requête (pour invité ou fallback)
        email = self.request.query_params.get('email')
        phone = self.request.query_params.get('phone')

        if email:
            user = User.objects.filter(email=email).first()
            if user:
                return queryset.filter(user=user)
            return queryset.filter(guest__email=email)
        
        if phone:
            return queryset.filter(guest__phone_number=phone)

        # Si non connecté et pas de filtre, on ne renvoie rien pour la sécurité
        return queryset.none()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        items_data = data.get('items', [])
        amount = data.get('amount')
        address = data.get('deliveryAddress', 'Livraison CleanGirls')
        
        # Infos de transaction de paiement éventuelles
        payment_info = data.get('payment', None)

        if not items_data or not amount:
            return Response({"error": "Données de commande incomplètes (montant ou articles manquants)"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order(
            total_amount_fcfa=amount,
            delivery_address=address,
            status='PENDING'
        )

        # Associer à un utilisateur connecté ou créer une session d'invité
        if request.user.is_authenticated:
            order.user = request.user
        else:
            # Essayer de créer une session d'invité
            guest_name = data.get('guestName', 'Invitée')
            guest_phone = data.get('guestPhone', payment_info.get('phone_debited') if payment_info else '')
            guest_email = data.get('guestEmail', '')

            guest_session = GuestSession.objects.create(
                first_name=guest_name,
                phone_number=guest_phone,
                email=guest_email
            )
            order.guest = guest_session

        order.save()

        # Créer les articles de commande (OrderItem)
        for item in items_data:
            product_id = item.get('productId')
            qty = item.get('quantity', 1)
            size = item.get('selectedSize', '')
            price = item.get('priceFCFA')

            order_item = OrderItem(
                order=order,
                quantity=qty,
                selected_size=size,
                price_fcfa=price
            )

            # Résoudre le produit
            if product_id.startswith('cos-'):
                db_id = int(product_id.split('-')[1])
                order_item.cosmetic_product = get_object_or_404(CosmeticProduct, id=db_id)
                # Optionnel : réduire le stock
                product = order_item.cosmetic_product
                if product.stock_quantity >= qty:
                    product.stock_quantity -= qty
                    product.save()
            elif product_id.startswith('clt-'):
                db_id = int(product_id.split('-')[1])
                order_item.clothing_product = get_object_or_404(ClothingProduct, id=db_id)
                # Optionnel : réduire le stock de la taille spécifique
                product = order_item.clothing_product
                size_lower = size.lower()
                if size_lower == 'xs' and product.stock_xs >= qty:
                    product.stock_xs -= qty
                elif size_lower == 's' and product.stock_s >= qty:
                    product.stock_s -= qty
                elif size_lower == 'm' and product.stock_m >= qty:
                    product.stock_m -= qty
                elif size_lower == 'l' and product.stock_l >= qty:
                    product.stock_l -= qty
                elif size_lower == 'xl' and product.stock_xl >= qty:
                    product.stock_xl -= qty
                product.save()
            
            order_item.save()

        # Enregistrer la transaction de paiement si présente
        if payment_info:
            operator = payment_info.get('operator')
            phone_debited = payment_info.get('phone_debited')
            transaction_id = payment_info.get('transaction_id')
            ussd_string = payment_info.get('ussd_string', '')
            payment_mode = payment_info.get('payment_mode', 'MERCHANT')

            PaymentTransaction.objects.create(
                order=order,
                operator=operator,
                payment_mode=payment_mode,
                amount_fcfa=amount,
                phone_debited=phone_debited,
                ussd_string_dialed=ussd_string,
                transaction_id=transaction_id,
                is_verified=False
            )
            # Puisque le paiement a été initié et simulé comme réussi côté client, on marque comme PAID
            order.status = 'PENDING'
            order.save()

        # Incrémenter les points de fidélité pour le client connecté
        if order.user:
            profile, _ = UserProfile.objects.get_or_create(user=order.user)
            # 1 point par tranche de 1000 FCFA d'achat
            profile.loyalty_points += int(amount / 1000)
            profile.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FavoriteViewSet(viewsets.ViewSet):
    """
    Gestion des favoris des clientes.
    """
    def list(self, request):
        if not request.user.is_authenticated:
            # Fallback si l'email est passé dans les query params
            email = request.query_params.get('email')
            if email:
                user = User.objects.filter(email=email).first()
                if user:
                    favs = FavoriteItem.objects.filter(user=user)
                    return Response(self._serialize_favorites(favs))
            return Response([])

        favs = FavoriteItem.objects.filter(user=request.user)
        return Response(self._serialize_favorites(favs))

    def _serialize_favorites(self, favs):
        result = []
        for fav in favs:
            if fav.cosmetic_product:
                result.append(f"cos-{fav.cosmetic_product.id}")
            elif fav.clothing_product:
                result.append(f"clt-{fav.clothing_product.id}")
        return result

    def create(self, request):
        """
        Active ou désactive un favori (Toggle).
        """
        product_id = request.data.get('productId')
        email = request.data.get('email')  # Fallback si non connecté par session

        if not product_id:
            return Response({"error": "ID Produit requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Résoudre l'utilisateur
        user = request.user
        if not user.is_authenticated and email:
            user = User.objects.filter(email=email).first()

        if not user or not user.is_authenticated:
            return Response({"error": "Veuillez vous connecter pour gérer vos favoris"}, status=status.HTTP_401_UNAUTHORIZED)

        # Résoudre le produit et basculer l'état de favori
        cosmetic = None
        clothing = None
        
        if product_id.startswith('cos-'):
            db_id = int(product_id.split('-')[1])
            cosmetic = get_object_or_404(CosmeticProduct, id=db_id)
            fav_qs = FavoriteItem.objects.filter(user=user, cosmetic_product=cosmetic)
            if fav_qs.exists():
                fav_qs.delete()
                return Response({"status": "removed", "productId": product_id})
            else:
                FavoriteItem.objects.create(user=user, cosmetic_product=cosmetic)
                return Response({"status": "added", "productId": product_id})
        
        elif product_id.startswith('clt-'):
            db_id = int(product_id.split('-')[1])
            clothing = get_object_or_404(ClothingProduct, id=db_id)
            fav_qs = FavoriteItem.objects.filter(user=user, clothing_product=clothing)
            if fav_qs.exists():
                fav_qs.delete()
                return Response({"status": "removed", "productId": product_id})
            else:
                FavoriteItem.objects.create(user=user, clothing_product=clothing)
                return Response({"status": "added", "productId": product_id})

        return Response({"error": "ID Produit invalide"}, status=status.HTTP_400_BAD_REQUEST)


class FacebookPostsView(APIView):
    """
    Preuve sociale : renvoie les publications Facebook simulées ou réelles.
    """
    def get(self, request):
        # En production, ce service interrogerait l'API Graph Facebook
        # En utilisant la configuration dans le modèle FacebookConfig.
        # Ici, nous retournons un flux simulé pour le design élégant.
        return Response([
            {
                "id": "fb-001",
                "image": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?q=80&w=500",
                "text": "Sublimée par le Sérum Éclat Infini d'Or de Kribi ✨ Ma peau n'a jamais été aussi lumineuse et unifiée ! Merci @CleanGirls pour cette merveille de soin camerounais.",
                "likes": 342,
                "comments": 28,
                "date": "Hier, à 14h30"
            },
            {
                "id": "fb-002",
                "image": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?q=80&w=500",
                "text": "Le Kaba Moderne Rose Poudré & Or fait fureur ! Commandé en ligne et reçu en 24h à Yaoundé. L'atelier fait un travail de broderie fantastique. 😍👗",
                "likes": 189,
                "comments": 14,
                "date": "Il y a 3 jours"
            }
        ])


# ─── WebPush Status Check ───────────────────────────────────────────────────

class WebpushSubscriptionStatusView(APIView):
    """
    Vérifie si une souscription WebPush existe pour le navigateur/utilisateur courant.
    """
    def post(self, request):
        endpoint = request.data.get('endpoint')
        user = request.user

        if user and user.is_authenticated:
            from webpush.models import PushInformation
            if PushInformation.objects.filter(user=user).exists():
                return Response({"subscribed": True, "message": "Utilisateur déjà abonné."})

        if endpoint:
            from webpush.models import SubscriptionInfo
            if SubscriptionInfo.objects.filter(endpoint=endpoint).exists():
                return Response({"subscribed": True, "message": "Navigateur déjà abonné."})

        return Response({"subscribed": False, "message": "Aucun abonnement valide."})

