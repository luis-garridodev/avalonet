from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CharacterViewSet, PostViewSet, search_spotify_tracks

router = DefaultRouter()
router.register(r'characters', CharacterViewSet)
router.register(r'posts', PostViewSet)

urlpatterns = [
    # Colocamos a rota do Spotify no topo para ter prioridade
    path('spotify/search/', search_spotify_tracks, name='spotify-search'),
    
    # O roteador automático fica por último
    path('', include(router.urls)),
]