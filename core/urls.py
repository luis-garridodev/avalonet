from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Importando a nossa view de Registro recém-criada
from roleplay.views import NotificationViewSet, RegisterView

# Router para ViewSets
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('roleplay.urls')),
    path('api/', include(router.urls)),
    
    # Rota de Login (Gera o Token)
    path('api/login/', obtain_auth_token, name='api_token_auth'), 
    
    # NOVA ROTA: Cadastro de novos usuários
    path('api/register/', RegisterView.as_view(), name='api_register'),
    
    # Rotas para as páginas HTML (templates)
    path('', TemplateView.as_view(template_name='index.html')),
    path('login.html', TemplateView.as_view(template_name='login.html')),
]

# Libera o acesso às imagens locais via URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)