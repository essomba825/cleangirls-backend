# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    """
    Modèle représentant une catégorie de produits (ex: Soin Visage, Prêt-à-porter).
    Sert à la fois pour la boutique cosmétique et la boutique mode.
    """
    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    slug = models.SlugField(unique=True, verbose_name="Slug d'URL")
    description = models.TextField(blank=True, verbose_name="Description de la catégorie")
    icon_name = models.CharField(max_length=50, blank=True, verbose_name="Nom de l'icône Lucide")
    store_type = models.CharField(
        max_length=20,
        choices=[('COSMETIC', 'Cosmétique'), ('CLOTHING', 'Prêt-à-porter')],
        default='COSMETIC',
        verbose_name="Type de boutique associé"
    )

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_store_type_display()})"


class CosmeticProduct(models.Model):
    """
    Représente un produit cosmétique haut de gamme de la gamme CleanGirls.
    Intègre les prix en FCFA et les notes des utilisatrices.
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        limit_choices_to={'store_type': 'COSMETIC'},
        related_name="cosmetics",
        verbose_name="Catégorie"
    )
    name = models.CharField(max_length=200, verbose_name="Nom du soin")
    slug = models.SlugField(unique=True, verbose_name="Slug d'URL")
    description = models.TextField(verbose_name="Description de l'onguent ou soin")
    price_fcfa = models.PositiveIntegerField(verbose_name="Prix en FCFA")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="URL de l'image (CDN/Unsplash)")
    image_file = models.ImageField(
        upload_to='products/images/', blank=True, null=True,
        verbose_name="Image uploadée (prioritaire sur l'URL CDN)"
    )
    video_file = models.FileField(
        upload_to='products/videos/', blank=True, null=True,
        verbose_name="Vidéo produit (MP4/WebM recommandé)"
    )
    is_new = models.BooleanField(default=False, verbose_name="Marquer comme nouveauté")
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(1.00), MaxValueValidator(5.00)],
        verbose_name="Note moyenne sur 5"
    )
    stock_quantity = models.PositiveIntegerField(default=50, verbose_name="Quantité disponible")

    class Meta:
        verbose_name = "Produit Cosmétique"
        verbose_name_plural = "Produits Cosmétiques"
        ordering = ['-is_new', '-rating']

    def __str__(self):
        return self.name


class ClothingProduct(models.Model):
    """
    Représente un vêtement de prêt-à-porter exclusif (ex: Kaba Moderne, Robe Ndop).
    Gère les tailles et les disponibilités spécifiques.
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        limit_choices_to={'store_type': 'CLOTHING'},
        related_name="clothes",
        verbose_name="Catégorie Mode"
    )
    name = models.CharField(max_length=200, verbose_name="Nom de la création")
    slug = models.SlugField(unique=True, verbose_name="Slug d'URL")
    description = models.TextField(verbose_name="Description de la coupe et tissus")
    price_fcfa = models.PositiveIntegerField(verbose_name="Prix d'atelier en FCFA")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="URL de l'image (CDN/Unsplash)")
    image_file = models.ImageField(
        upload_to='products/images/', blank=True, null=True,
        verbose_name="Image uploadée (prioritaire sur l'URL CDN)"
    )
    video_file = models.FileField(
        upload_to='products/videos/', blank=True, null=True,
        verbose_name="Vidéo produit (MP4/WebM recommandé)"
    )
    is_new = models.BooleanField(default=False, verbose_name="Marquer comme pièce récente")
    
    # Tailles gérées sous forme de stocks distincts
    stock_xs = models.PositiveIntegerField(default=5, verbose_name="Stock Taille XS")
    stock_s = models.PositiveIntegerField(default=10, verbose_name="Stock Taille S")
    stock_m = models.PositiveIntegerField(default=10, verbose_name="Stock Taille M")
    stock_l = models.PositiveIntegerField(default=5, verbose_name="Stock Taille L")
    stock_xl = models.PositiveIntegerField(default=3, verbose_name="Stock Taille XL")

    class Meta:
        verbose_name = "Création Mode"
        verbose_name_plural = "Créations Mode"
        ordering = ['-is_new', 'name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    Profil étendu pour les clientes enregistrées sur la PWA CleanGirls.
    Permet la fidélisation et la conservation des données de paiement MoMo.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro de téléphone Mobile Money (+237)"
    )
    receive_newsletters = models.BooleanField(
        default=True,
        verbose_name="S'abonner aux newsletters de luxe"
    )
    loyalty_points = models.PositiveIntegerField(
        default=0,
        verbose_name="Points privilèges cumulés"
    )

    class Meta:
        verbose_name = "Profil Cliente"
        verbose_name_plural = "Profils Clientes"

    def __str__(self):
        return f"Profil de {self.user.first_name or self.user.username}"


class GuestSession(models.Model):
    """
    Session d'invité temporaire pour l'Express Checkout sans mot de passe.
    Persisté en sessionStorage côté client et lié aux commandes.
    """
    first_name = models.CharField(max_length=100, verbose_name="Prénom de l'invitée")
    phone_number = models.CharField(max_length=20, verbose_name="Téléphone de facturation MoMo")
    email = models.EmailField(blank=True, verbose_name="Email de contact (facultatif)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'enregistrement")

    class Meta:
        verbose_name = "Session Invitée"
        verbose_name_plural = "Sessions Invitées"
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitée {self.first_name} - {self.phone_number}"


class Order(models.Model):
    """
    Modèle de commande regroupant les articles réservés et le statut logistique.
    """
    STATUS_CHOICES = [
        ('PENDING', 'En attente de règlement'),
        ('PAID', 'Payé — En cours de préparation'),
        ('SHIPPED', 'Colis Expédié'),
        ('DELIVERED', 'Livré à Domicile'),
        ('CANCELLED', 'Annulé')
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Membre"
    )
    guest = models.ForeignKey(
        GuestSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Invitée"
    )
    total_amount_fcfa = models.PositiveIntegerField(verbose_name="Montant total en FCFA")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut Logistique"
    )
    delivery_address = models.TextField(verbose_name="Adresse ou point de livraison au Cameroun")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'achat")

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']

    def __str__(self):
        owner = self.user.first_name if self.user else (self.guest.first_name if self.guest else "Inconnu")
        return f"Commande #{self.id} par {owner} ({self.total_amount_fcfa} FCFA)"


class OrderItem(models.Model):
    """
    Modèle représentant un article d'une commande (cosmétique ou vêtement).
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Commande")
    cosmetic_product = models.ForeignKey(
        CosmeticProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Produit Cosmétique"
    )
    clothing_product = models.ForeignKey(
        ClothingProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Création Mode"
    )
    selected_size = models.CharField(max_length=10, blank=True, verbose_name="Taille sélectionnée")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    price_fcfa = models.PositiveIntegerField(verbose_name="Prix unitaire en FCFA")

    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"

    def __str__(self):
        item_name = self.cosmetic_product.name if self.cosmetic_product else (self.clothing_product.name if self.clothing_product else "Produit inconnu")
        return f"{self.quantity}x {item_name} (Commande #{self.order.id})"


class PaymentTransaction(models.Model):
    """
    Trace de paiement Mobile Money liée à une commande pour rapprochement comptable.
    Enregistre les codes marchands MTN et Orange ou les dépôts vers des numéros particuliers.
    """
    OPERATOR_CHOICES = [
        ('MTN', 'MTN Mobile Money'),
        ('ORANGE', 'Orange Money')
    ]

    MODE_CHOICES = [
        ('MERCHANT', 'Code Marchand Officiel'),
        ('DIRECT_DEPOSIT', 'Dépôt vers Compte Particulier')
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    operator = models.CharField(max_length=15, choices=OPERATOR_CHOICES, verbose_name="Opérateur")
    payment_mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='MERCHANT',
        verbose_name="Mode de réception du paiement"
    )
    amount_fcfa = models.PositiveIntegerField(verbose_name="Somme payée en FCFA")
    phone_debited = models.CharField(max_length=20, verbose_name="Numéro MoMo débité")
    ussd_string_dialed = models.CharField(max_length=100, verbose_name="Ligne USSD composée")
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="ID Transaction Opérateur")
    is_verified = models.BooleanField(default=False, verbose_name="Transaction vérifiée par l'administrateur")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation manuelle")

    class Meta:
        verbose_name = "Transaction Mobile Money"
        verbose_name_plural = "Transactions Mobile Money"

    def __str__(self):
        return f"Paiement {self.operator} ({self.get_payment_mode_display()}) - Ref: {self.transaction_id}"


class FavoriteItem(models.Model):
    """
    Modèle de liaison pour stocker les produits favoris des clientes connectées.
    Supporte les clés étrangères optionnelles vers les cosmétiques ou les créations mode.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites", verbose_name="Cliente")
    cosmetic_product = models.ForeignKey(
        CosmeticProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favorited_by",
        verbose_name="Produit Cosmétique"
    )
    clothing_product = models.ForeignKey(
        ClothingProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favorited_by",
        verbose_name="Création Mode"
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté le")

    class Meta:
        verbose_name = "Article Favori"
        verbose_name_plural = "Articles Favoris"
        unique_together = [('user', 'cosmetic_product'), ('user', 'clothing_product')]

    def __str__(self):
        item_name = self.cosmetic_product.name if self.cosmetic_product else (self.clothing_product.name if self.clothing_product else "Inconnu")
        return f"{self.user.first_name} adore {item_name}"


class FacebookConfig(models.Model):
    """
    Configuration de synchronisation pour le module de preuve sociale de la PWA.
    Permet la récupération dynamique de publications du feed Facebook de la marque.
    """
    page_id = models.CharField(max_length=100, verbose_name="ID de Page Facebook")
    access_token = models.CharField(max_length=255, verbose_name="Token Graph API")
    cache_ttl_minutes = models.PositiveIntegerField(default=60, verbose_name="Durée de cache (minutes)")

    class Meta:
        verbose_name = "Configuration Facebook"
        verbose_name_plural = "Configurations Facebook"

    def __str__(self):
        return f"Liaison Page ID: {self.page_id}"
