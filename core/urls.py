from django.contrib import admin
from django.urls import path, include
from django.conf import settings # <-- Adicione esta linha
from django.conf.urls.static import static # <-- E esta linha

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('roleplay.urls')),
]

# Libera o acesso às imagens durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)