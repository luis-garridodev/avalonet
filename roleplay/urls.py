from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CharacterViewSet, PostViewSet, CommentViewSet, DirectMessageViewSet, ReportViewSet, search_spotify_tracks

router = DefaultRouter()
router.register(r'characters', CharacterViewSet)
router.register(r'posts', PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'messages', DirectMessageViewSet)
# NOVO: Rota de denúncias
router.register(r'reports', ReportViewSet, basename='report') 

urlpatterns = [
    path('', include(router.urls)),
    path('spotify/search/', search_spotify_tracks, name='spotify-search'),
]