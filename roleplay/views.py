import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Character, Post
from .serializers import CharacterSerializer, PostSerializer

class CharacterViewSet(viewsets.ModelViewSet):
    """
    Controla todas as ações da Máscara (Listar, Criar, Atualizar, Deletar).
    """
    queryset = Character.objects.all()
    serializer_class = CharacterSerializer

class PostViewSet(viewsets.ModelViewSet):
    """
    Controla o Feed. Já configurado para mostrar os posts mais recentes primeiro.
    """
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer


@api_view(['GET'])
def search_spotify_tracks(request):
    """
    Busca faixas no Spotify a partir do parâmetro 'q' na URL.
    Exemplo: /api/spotify/search/?q=misfits
    """
    query = request.GET.get('q', '')
    if not query:
        return Response([])

    # Autenticação automática com o Spotify usando as chaves secretas
    client_credentials_manager = SpotifyClientCredentials(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET
    )
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Faz a busca por faixas limitando a 5 resultados
    results = sp.search(q=query, limit=5, type='track')
    tracks = []

    for item in results['tracks']['items']:
        tracks.append({
            'id': item['id'],
            'name': item['name'],
            'artist': item['artists'][0]['name'],
            'album_cover': item['album']['images'][0]['url'] if item['album']['images'] else None,
            'spotify_url': item['external_urls']['spotify'],
        })

    return Response(tracks)