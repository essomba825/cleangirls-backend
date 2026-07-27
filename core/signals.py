# signals.py
import logging
import json
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from webpush import send_user_notification, send_group_notification

from .models import Order, PaymentTransaction

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_order_owner_email(order):
    if order.user and order.user.email:
        return order.user.email
    if order.guest and order.guest.email:
        return order.guest.email
    return None


def _send_webpush(user, title, body, url="/"):
    payload = json.dumps({
        "head": title,
        "body": body,
        "url": url,
        "icon": "/favicon.png",
        "badge": "/favicon.png",
        "vibrate": [200, 100, 200, 100, 400],
    })
    try:
        send_user_notification(user=user, payload=payload, ttl=3600)
        logger.info(f"[WebPush] ✅ Envoyé à {user.username}: {title}")
    except Exception as e:
        logger.warning(f"[WebPush] ❌ Échec pour {user.username}: {e}")


def _send_webpush_group(group_name, title, body, url="/"):
    """Envoie un WebPush à tout un groupe (ex: 'all', 'promotions')."""
    payload = json.dumps({
        "head": title,
        "body": body,
        "url": url,
        "icon": "/favicon.png",
        "badge": "/favicon.png",
        "vibrate": [200, 100, 200],
    })
    try:
        send_group_notification(group_name=group_name, payload=payload, ttl=3600)
        logger.info(f"[WebPush] ✅ Groupe '{group_name}' notifié: {title}")
    except Exception as e:
        logger.warning(f"[WebPush] ❌ Échec groupe '{group_name}': {e}")


def _send_webpush_to_all_admins(title, body, url="/admin"):
    admins = User.objects.filter(is_staff=True)
    for admin in admins:
        _send_webpush(admin, title, body, url)


def _send_email_safe(subject, template_name, context, recipient):
    """
    Envoie un email HTML avec fallback texte brut.
    :param subject: Sujet de l'email
    :param template_name: Chemin du template (ex: 'emails/order_created.html')
    :param context: Dictionnaire de contexte pour le template
    :param recipient: Adresse email du destinataire
    """
    try:
        # Rendu du HTML
        html_content = render_to_string(template_name, context)
        # Texte brut simple (peut être généré plus tard via un bloc template)
        text_content = (
            f"Bonjour {context.get('owner_name', '')},\n\n"
            f"{context.get('body_preview', 'Voir les détails de votre commande.')}\n\n"
            f"Merci de votre confiance,\nL'équipe CleanGirls"
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"[Email] ✅ HTML envoyé à {recipient}: {subject}")
    except Exception as e:
        logger.error(f"[Email] ❌ Erreur envoi à {recipient}: {e}")


STATUS_LABELS = {
    'PENDING':   '🕐 En attente de règlement',
    'PAID':      '✅ Payé — En cours de préparation',
    'SHIPPED':   '📦 Colis Expédié',
    'DELIVERED': '🎁 Livré à Domicile',
    'CANCELLED': '❌ Annulé',
}


# ─── Signal : tracking ancien statut ─────────────────────────────────────────

@receiver(pre_save, sender=Order)
def _track_old_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# ─── Signal : nouvelle commande créée ────────────────────────────────────────

@receiver(post_save, sender=Order)
def notify_order_status_change(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    owner_name = (
        instance.user.first_name if instance.user
        else (instance.guest.first_name if instance.guest else "Cliente")
    )
    owner_email = _get_order_owner_email(instance)
    site_url = getattr(settings, 'SITE_URL', 'https://example.com')

    # ── Cas 1 : Nouvelle commande ─────────────────────────────────────────────
    if created:
        title = f"🛍️ Commande #{instance.id} reçue !"
        body = (
            f"Bonjour {owner_name}, votre commande de {instance.total_amount_fcfa} FCFA "
            f"a bien été enregistrée. Nous confirmons dès réception du paiement."
        )

        # Notifier la cliente connectée par WebPush
        if instance.user:
            _send_webpush(instance.user, title, body, "/orders")

        # Notifier par email (user ou guest)
        if owner_email:
            context = {
                "owner_name": owner_name,
                "order": instance,
                "site_url": site_url,
                "body_preview": body,
            }
            _send_email_safe(
                subject=f"[CleanGirls] Commande #{instance.id} reçue",
                template_name="emails/order_created.html",
                context=context,
                recipient=owner_email,
            )

        # Notifier les admins
        admin_body = (
            f"Nouvelle commande #{instance.id} | {owner_name} | "
            f"{instance.total_amount_fcfa} FCFA"
        )
        _send_webpush_to_all_admins(
            "🆕 Nouvelle Commande",
            admin_body,
            f"/admin/shop/order/{instance.id}/change/"
        )
        return

    # ── Cas 2 : Changement de statut ─────────────────────────────────────────
    if new_status == old_status:
        return  # Pas de changement réel

    label = STATUS_LABELS.get(new_status, new_status)
    title = f"Commande #{instance.id} — {label}"
    body = f"Bonjour {owner_name}, votre commande CleanGirls est maintenant : {label}."

    if instance.user:
        _send_webpush(instance.user, title, body, "/orders")

    if owner_email:
        context = {
            "owner_name": owner_name,
            "order": instance,
            "new_status": new_status,
            "status_label": label,
            "site_url": site_url,
            "body_preview": body,
        }
        _send_email_safe(
            subject=f"[CleanGirls] Commande #{instance.id} — {label}",
            template_name="emails/order_status_update.html",
            context=context,
            recipient=owner_email,
        )

    admin_body = f"Statut → {label} | {owner_name} | {instance.total_amount_fcfa} FCFA"
    _send_webpush_to_all_admins(
        f"📋 Commande #{instance.id} mise à jour",
        admin_body,
        f"/admin/shop/order/{instance.id}/change/"
    )


# ─── Signal : paiement MoMo vérifié ──────────────────────────────────────────

@receiver(post_save, sender=PaymentTransaction)
def notify_payment_verified(sender, instance, created, **kwargs):
    order = instance.order
    owner_name = (
        order.user.first_name if order.user
        else (order.guest.first_name if order.guest else "Cliente")
    )
    owner_email = _get_order_owner_email(order)
    site_url = getattr(settings, 'SITE_URL', 'https://example.com')

    # ── Cas 1 : Nouveau paiement initié (même non vérifié) ───────────────────
    if created:
        admin_body = (
            f"Paiement initié | {instance.operator} | "
            f"{instance.amount_fcfa} FCFA | Commande #{order.id} | "
            f"Tel: {instance.phone_debited}"
        )
        _send_webpush_to_all_admins(
            "💳 Nouveau paiement à vérifier",
            admin_body,
            f"/admin/shop/paymenttransaction/{instance.id}/change/"
        )
        return

    # ── Cas 2 : Paiement vérifié par un admin ────────────────────────────────
    if not instance.is_verified:
        return

    title = f"💳 Paiement {instance.operator} confirmé !"
    body = (
        f"Bonjour {owner_name}, votre paiement de {instance.amount_fcfa} FCFA "
        f"via {instance.operator} a été vérifié. "
        f"Votre commande #{order.id} est maintenant en préparation !"
    )

    if order.user:
        _send_webpush(order.user, title, body, "/orders")

    if owner_email:
        context = {
            "owner_name": owner_name,
            "order": order,
            "instance": instance,
            "site_url": site_url,
            "body_preview": body,
        }
        _send_email_safe(
            subject=f"[CleanGirls] Paiement confirmé — Commande #{order.id}",
            template_name="emails/payment_verified.html",
            context=context,
            recipient=owner_email,
        )

    admin_body = (
        f"Paiement #{instance.id} vérifié | {instance.operator} | "
        f"{instance.amount_fcfa} FCFA | Commande #{order.id}"
    )
    _send_webpush_to_all_admins(
        "✅ Paiement vérifié",
        admin_body,
        "/admin/shop/paymenttransaction/"
    )