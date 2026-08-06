import requests
from django.conf import settings
from django.db.models import Q
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from .models import (
    Character, Post, Comment, DirectMessage, Report, Notification, 
    Achievement, CharacterAchievement, Universe, UniverseMessage, PostReaction, Saga
)
from .serializers import (
    CharacterSerializer, PostSerializer, CommentSerializer, 
    DirectMessageSerializer, ReportSerializer, RegisterSerializer, NotificationSerializer,
    UniverseSerializer, UniverseMessageSerializer, SagaSerializer
)
from django.utils import timezone
import re
from collections import Counter

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
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'bio']

    def create(self, request, *args, **kwargs):
        player = request.user
        char_count = Character.objects.filter(player=player).count()
        
        limit = 5 if player.is_premium else player.max_characters
        
        if char_count >= limit:
            if not player.is_premium:
                return Response({'error': 'Limite de 2 personas na conta grátis. Assine o Premium na Loja para ter até 5!'}, status=400)
            else:
                return Response({'error': 'Você atingiu o limite máximo de 5 personas do plano Premium.'}, status=400)
                
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
        target_character = self.get_object()
        persona_id = request.data.get('persona_id')
        
        try:
            my_persona = Character.objects.get(id=persona_id, player=request.user)
        except Character.DoesNotExist:
            return Response({'error': 'Persona não encontrada ou sem permissão.'}, status=400)

        if target_character == my_persona:
            return Response({'error': 'Não podes seguir a ti mesmo!'}, status=400)

        if target_character.followers.filter(id=my_persona.id).exists():
            target_character.followers.remove(my_persona)
            is_following = False
        else:
            target_character.followers.add(my_persona)
            is_following = True
            Notification.objects.create(sender=my_persona, recipient=target_character, notification_type='follow')

        return Response({'is_following': is_following, 'message': 'Ação concluída com sucesso!'})

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

    @action(detail=True, methods=['post'])
    def claim_quest(self, request, pk=None):
        character = self.get_object()
        quest_type = request.data.get('quest_type')
        hoje = timezone.now().date()

        if quest_type == 'post':
            if character.last_daily_post == hoje:
                return Response({'error': 'Você já resgatou a missão de Post hoje! Volte amanhã.'}, status=400)
            character.last_daily_post = hoje
            character.fl_coins += 50
            character.save()
            return Response({'message': 'Missão concluída! +50 FL Coins', 'fl_coins': character.fl_coins})

        elif quest_type == 'chat':
            if character.last_daily_chat == hoje:
                return Response({'error': 'Você já resgatou a missão de Chat hoje! Volte amanhã.'}, status=400)
            character.last_daily_chat = hoje
            character.fl_coins += 10
            character.save()
            return Response({'message': 'Missão concluída! +10 FL Coins', 'fl_coins': character.fl_coins})

        return Response({'error': 'Tipo de missão inválida.'}, status=400)


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
        if post.author != persona:
            Notification.objects.create(sender=persona, recipient=post.author, notification_type='like_post', post=post)
        return Response({"status": "curtido", "total_likes": post.total_likes})
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author.player != request.user:
            return Response({"erro": "Você não pode apagar o post de outra pessoa."}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def trending(self, request):
        recent_posts = Post.objects.all().order_by('-created_at')[:50]
        hashtags = []
        for post in recent_posts:
            if post.content:
                tags = re.findall(r"#\w+", post.content)
                hashtags.extend([tag.lower() for tag in tags])
        tag_counts = Counter(hashtags)
        top_tags = tag_counts.most_common(5)
        data = [{"tag": tag, "count": count} for tag, count in top_tags]
        return Response(data)

    @action(detail=True, methods=['post'])
    def toggle_reaction(self, request, pk=None):
        post = self.get_object()
        persona_id = request.data.get('persona_id')
        emoji = request.data.get('emoji')
        
        if not persona_id or not emoji:
            return Response({'error': 'Parâmetros inválidos'}, status=400)
            
        reaction, created = PostReaction.objects.get_or_create(
            post=post, persona_id=persona_id, emoji=emoji
        )
        if not created:
            reaction.delete()
            
        summary = []
        for emj in ['❤️', '🔥', '😡', '👎', '😂', '🎉']:
            count = post.reactions.filter(emoji=emj).count()
            users_reacted = list(post.reactions.filter(emoji=emj).values_list('persona_id', flat=True))
            summary.append({'emoji': emj, 'count': count, 'users': users_reacted})
            
        return Response({'reactions': summary})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('created_at')
    serializer_class = CommentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
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
        if comment.author != persona:
            Notification.objects.create(sender=persona, recipient=comment.author, notification_type='like_comment', post=comment.post)
        return Response({"status": "curtido", "total_likes": comment.total_likes})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author.player != request.user:
            return Response({"erro": "Você não pode apagar o comentário de outra pessoa."}, status=403)
        return super().destroy(request, *args, **kwargs)


class DirectMessageViewSet(viewsets.ModelViewSet):
    queryset = DirectMessage.objects.all().order_by('created_at')
    serializer_class = DirectMessageSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        persona_id = self.request.query_params.get('persona_id')
        contact_id = self.request.query_params.get('contact_id')

        if persona_id and contact_id:
            return queryset.filter(
                Q(sender_id=persona_id, receiver_id=contact_id) | 
                Q(sender_id=contact_id, receiver_id=persona_id)
            )
        elif persona_id:
            return queryset.filter(Q(sender_id=persona_id) | Q(receiver_id=persona_id))
        return queryset

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


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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


class SagaViewSet(viewsets.ModelViewSet):
    queryset = Saga.objects.all().order_by('-created_at')
    serializer_class = SagaSerializer
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


def toggle_alpha_badge(request):
    if request.method == 'POST' and request.user.is_authenticated:
        persona = request.user.persona 
        persona.show_alpha_badge = not persona.show_alpha_badge
        persona.save()
        return JsonResponse({'status': 'sucesso', 'mostrar': persona.show_alpha_badge})


class UniverseViewSet(viewsets.ModelViewSet):
    queryset = Universe.objects.all().order_by('-created_at')
    serializer_class = UniverseSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # Trava de Limites de Universos
    def create(self, request, *args, **kwargs):
        player = request.user
        
        if not (player.is_superuser or (player.username and player.username.lower() == 'fangsblood')):
            universe_count = Universe.objects.filter(owner__player=player).count()
            limit = 3 if player.is_premium else 1
            
            if universe_count >= limit:
                plano = "VIP" if player.is_premium else "Grátis"
                return Response(
                    {'error': f'Limite atingido! Uma conta {plano} pode criar até {limit} Universo(s).'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        universe = self.get_object()
        persona_id = request.data.get('persona_id')
        
        try:
            persona = Character.objects.get(id=persona_id)
        except Character.DoesNotExist:
            return Response({'error': 'Persona não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if universe.privacy == 'open':
            universe.members.add(persona)
            return Response({'message': f'Entraste no universo {universe.name} com sucesso!'})
        else:
            universe.pending_members.add(persona)
            return Response({'message': 'Pedido de entrada enviado aos administradores do Universo.'})
            
    # Listar solicitações pendentes (Dono do Universo)
    @action(detail=True, methods=['get'])
    def requests(self, request, pk=None):
        universe = self.get_object()
        pending = universe.pending_members.all()
        data = [
            {
                "id": p.id,
                "name": p.name,
                "avatar": p.avatar.url if p.avatar else "",
                "species": p.species
            } for p in pending
        ]
        return Response(data)

    # Aprovar solicitação pendente
    @action(detail=True, methods=['post'])
    def approve_request(self, request, pk=None):
        universe = self.get_object()
        requester_id = request.data.get('requester_id')
        try:
            requester = Character.objects.get(id=requester_id)
            if requester in universe.pending_members.all():
                universe.pending_members.remove(requester)
                universe.members.add(requester)
                return Response({'message': 'Usuário aprovado com sucesso!'})
            return Response({'error': 'Solicitação não encontrada.'}, status=status.HTTP_400_BAD_REQUEST)
        except Character.DoesNotExist:
            return Response({'error': 'Persona não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    # Recusar solicitação pendente
    @action(detail=True, methods=['post'])
    def reject_request(self, request, pk=None):
        universe = self.get_object()
        requester_id = request.data.get('requester_id')
        try:
            requester = Character.objects.get(id=requester_id)
            if requester in universe.pending_members.all():
                universe.pending_members.remove(requester)
                return Response({'message': 'Usuário recusado.'})
            return Response({'error': 'Solicitação não encontrada.'}, status=status.HTTP_400_BAD_REQUEST)
        except Character.DoesNotExist:
            return Response({'error': 'Persona não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get', 'post'])
    def chat(self, request, pk=None):
        universe = self.get_object()
        
        if request.method == 'GET':
            messages = universe.messages.all().order_by('created_at')
            serializer = UniverseMessageSerializer(messages, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            sender_id = request.data.get('sender_id')
            content = request.data.get('content', '')
            image = request.FILES.get('image', None)
            
            try:
                sender = Character.objects.get(id=sender_id)
            except Character.DoesNotExist:
                return Response({'error': 'Remetente inválido.'}, status=status.HTTP_400_BAD_REQUEST)
                
            msg = UniverseMessage.objects.create(
                universe=universe,
                sender=sender,
                content=content,
                image=image
            )
            serializer = UniverseMessageSerializer(msg)
            return Response(serializer.data, status=status.HTTP_201_CREATED)