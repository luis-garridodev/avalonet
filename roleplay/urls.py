from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importando todas as views (Adicionei SagaViewSet e NotificationViewSet)
from .views import (
    CharacterViewSet, 
    PostViewSet, 
    CommentViewSet, 
    DirectMessageViewSet, 
    ReportViewSet, 
    UniverseViewSet,
    SagaViewSet,             # <-- Adicionado para as Sagas
    NotificationViewSet,     # <-- Adicionado para as Notificações
    search_spotify_tracks
)

router = DefaultRouter()

# Registrando os endpoints principais
router.register(r'characters', CharacterViewSet)
router.register(r'posts', PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'messages', DirectMessageViewSet)
router.register(r'reports', ReportViewSet, basename='report') 
router.register(r'universes', UniverseViewSet)

# NOVO: Registrando Sagas e Notificações que o frontend já chama
router.register(r'sagas', SagaViewSet, basename='saga')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # O router gera automaticamente rotas como /api/universes/1/requests/
    path('', include(router.urls)),
    path('spotify/search/', search_spotify_tracks, name='spotify-search'),
]