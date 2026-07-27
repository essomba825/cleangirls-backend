from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse  # <-- 1. Import obligatoire pour la réponse
from webpush.views import save_info as webpush_save_info

# <-- 2. On définit la fonction PING ICI, AVANT urlpatterns
def ping(request):
    return HttpResponse("pong", status=200)


urlpatterns = [
    path('ping/', ping, name='ping'),  # <-- 3. Maintenant Python reconnaît 'ping' !
    path('admin/', admin.site.urls),
    path('api/v1/', include('core.urls')),
    path('api/v1/admin/', include('core.admin_urls')),
    # django-webpush (include les routes jsi18n + service-worker.js)
    path('api/v1/webpush/', include('webpush.urls')),
    # Alias avec trailing slash pour la souscription (les navigateurs envoient le slash)
    path('api/v1/webpush/save_information/', webpush_save_info, name='save_webpush_info_slash'),
]

# Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)