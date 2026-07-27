# -*- coding: utf-8 -*-
from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication qui court-circuite la vérification CSRF pour les APIs REST.
    """
    def enforce_csrf(self, request):
        return  # Ne fait rien, contourne le contrôle CSRF
