import requests
from django.conf import settings
from django.db.models import Q
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model

from .models import Character, Post, Comment, DirectMessage, Report, Notification
from .serializers import (
    CharacterSerializer, PostSerializer, CommentSerializer, 
    DirectMessageSerializer, ReportSerializer, RegisterSerializer, NotificationSerializer
)

Player = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = Player.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class CharacterViewSet(viewsets.ModelViewSet):
    queryset = Character.objects.all()
    serializer_class = CharacterSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    # CORREÇÃO DA BUSCA: 'bio' ao invés de 'lore'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'bio']

    def create(self, request, *args, **kwargs):
        user = request.user
        if Character.objects.filter(player=user).count() >= 2:
            return Response({"erro": "Limite atingido."}, status=403)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(player=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.player != request.user:
            return Response({"erro": "Sem permissão."}, status=403)
        kwargs['partial'] = True 
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_personas(self, request):
        return Response(self.get_serializer(Character.objects.filter(player=request.user), many=True).data)

    @action(detail=True, methods=['post'])
    def toggle_follow(self, request, pk=None):
        target = self.get_object() 
        follower_id = request.data.get('follower_id') 
        if not follower_id: return Response({"erro": "ID não enviado."}, status=400)
        try: follower = Character.objects.get(id=follower_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Persona inválida."}, status=403)

        if target.id == follower.id: return Response({"erro": "Você não pode seguir a si mesmo!"}, status=400)

        if target.followers.filter(id=follower.id).exists():
            target.followers.remove(follower)
            return Response({"status": "unfollowed", "total_followers": target.total_followers})
        else:
            target.followers.add(follower)
            # GATILHO DE NOTIFICAÇÃO: Seguir
            Notification.objects.create(sender=follower, recipient=target, notification_type='follow')
            return Response({"status": "followed", "total_followers": target.total_followers})

    @action(detail=True, methods=['post'])
    def toggle_mute(self, request, pk=None):
        target = self.get_object() 
        persona_id = request.data.get('persona_id') 
        try: persona = Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Persona inválida."}, status=403)

        if persona.muted_characters.filter(id=target.id).exists():
            persona.muted_characters.remove(target)
            return Response({"status": "unmuted"})
        else:
            persona.muted_characters.add(target)
            return Response({"status": "muted"})

    @action(detail=True, methods=['get'])
    def followers_list(self, request, pk=None):
        return Response(self.get_serializer(self.get_object().followers.all(), many=True).data)

    @action(detail=True, methods=['get'])
    def following_list(self, request, pk=None):
        return Response(self.get_serializer(self.get_object().following.all(), many=True).data)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all() 
    serializer_class = PostSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Post.objects.all().order_by('-created_at')
        author_id = self.request.query_params.get('author_id')
        persona_id = self.request.query_params.get('persona_id')
        
        if author_id:
            queryset = queryset.filter(author__id=author_id)
        elif persona_id:
            try:
                persona = Character.objects.get(id=persona_id, player=self.request.user)
                muted_ids = persona.muted_characters.values_list('id', flat=True)
                queryset = queryset.exclude(author__id__in=muted_ids)
            except Character.DoesNotExist: pass
        return queryset

    @action(detail=True, methods=['post'])
    def toggle_like(self, request, pk=None):
        post = self.get_object()
        persona_id = request.data.get('persona_id')
        try: persona = Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Persona inválida."}, status=403)

        already_liked = post.likes.filter(id__in=Character.objects.filter(player=request.user)).first()
        if already_liked:
            if already_liked.id == persona.id:
                post.likes.remove(persona)
                return Response({"status": "descurtido", "total_likes": post.total_likes})
            return Response({"erro": f"Você já curtiu com '{already_liked.name}'."}, status=403)
            
        post.likes.add(persona)
        # GATILHO DE NOTIFICAÇÃO: Curtir Post
        if post.author != persona:
            Notification.objects.create(sender=persona, recipient=post.author, notification_type='like_post', post=post)
        return Response({"status": "curtido", "total_likes": post.total_likes})
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author.player != request.user:
            return Response({"erro": "Você não pode apagar o post de outra pessoa."}, status=403)
        return super().destroy(request, *args, **kwargs)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('created_at')
    serializer_class = CommentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    # GATILHO DE NOTIFICAÇÃO: Comentar
    def perform_create(self, serializer):
        comment = serializer.save()
        if comment.post.author != comment.author:
            Notification.objects.create(sender=comment.author, recipient=comment.post.author, notification_type='comment', post=comment.post)

    @action(detail=True, methods=['post'])
    def toggle_like(self, request, pk=None):
        comment = self.get_object()
        persona_id = request.data.get('persona_id')
        try: persona = Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Persona inválida."}, status=403)

        already_liked = comment.likes.filter(id__in=Character.objects.filter(player=request.user)).first()
        if already_liked:
            if already_liked.id == persona.id:
                comment.likes.remove(persona)
                return Response({"status": "descurtido", "total_likes": comment.total_likes})
            return Response({"erro": f"Você já curtiu com '{already_liked.name}'."}, status=403)
            
        comment.likes.add(persona)
        # GATILHO DE NOTIFICAÇÃO: Curtir Comentário
        if comment.author != persona:
            Notification.objects.create(sender=persona, recipient=comment.author, notification_type='like_comment', post=comment.post)
        return Response({"status": "curtido", "total_likes": comment.total_likes})
    # ADICIONE ESTA FUNÇÃO NO FINAL DO CommentViewSet:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author.player != request.user:
            return Response({"erro": "Você não pode apagar o comentário de outra pessoa."}, status=403)
        return super().destroy(request, *args, **kwargs)


class DirectMessageViewSet(viewsets.ModelViewSet):
    # ... (Seu código DirectMessageViewSet continua exatamente igual aqui, não mudei nada nele) ...
    queryset = DirectMessage.objects.all().order_by('created_at')
    serializer_class = DirectMessageSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def conversation(self, request):
        persona_id = request.query_params.get('persona_id')
        target_id = request.query_params.get('target_id')
        if not persona_id or not target_id: return Response({"erro": "Faltam IDs."}, status=400)
        try: Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Acesso negado."}, status=403)

        messages = DirectMessage.objects.filter(Q(sender_id=persona_id, receiver_id=target_id) | Q(sender_id=target_id, receiver_id=persona_id)).order_by('created_at')
        return Response(self.get_serializer(messages, many=True).data)

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        persona_id = request.query_params.get('persona_id')
        try: persona = Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist: return Response({"erro": "Acesso negado."}, status=403)

        messages = DirectMessage.objects.filter(Q(sender=persona) | Q(receiver=persona)).order_by('-created_at')
        conversations, seen_contacts = [], set()

        for msg in messages:
            other_character = msg.sender if msg.receiver == persona else msg.receiver
            if other_character.id not in seen_contacts:
                seen_contacts.add(other_character.id)
                conversations.append({
                    "contact_id": other_character.id,
                    "contact_name": other_character.name,
                    "contact_avatar": other_character.avatar.url if other_character.avatar else "",
                    "last_message": msg.content,
                    "last_message_date": msg.created_at,
                    "is_unread": not msg.is_read and msg.receiver == persona
                })
        return Response(conversations)

# --- NOVA VIEW DAS NOTIFICAÇÕES ---
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtra para mostrar apenas as notificações de quem está logado
        return Notification.objects.filter(recipient__player=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        persona_id = request.data.get('persona_id')
        if not persona_id: return Response({"erro": "ID da persona necessário."}, status=400)
        
        Notification.objects.filter(recipient_id=persona_id, recipient__player=request.user, is_read=False).update(is_read=True)
        return Response({"status": "Todas lidas"})

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().order_by('-created_at')
    serializer_class = ReportSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
def search_spotify_tracks(request):
    query = request.GET.get('q', '')
    if not query: return Response([])
    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    client_secret = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')
    auth_response = requests.post('https://accounts.spotify.com/api/token', data={'grant_type': 'client_credentials'}, auth=(client_id, client_secret))
    if auth_response.status_code != 200: return Response({"error": "Falha no Spotify"}, status=500)
    access_token = auth_response.json().get('access_token')
    search_response = requests.get(f'https://api.spotify.com/v1/search?q={query}&type=track&limit=5', headers={'Authorization': f'Bearer {access_token}'})
    if search_response.status_code != 200: return Response([])
    items = search_response.json().get('tracks', {}).get('items', [])
    return Response([{'id': i['id'], 'name': i['name'], 'artist': i['artists'][0]['name'], 'album_cover': i['album']['images'][0]['url'] if i['album']['images'] else ''} for i in items])