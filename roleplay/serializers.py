import mimetypes
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Player, Character, Post, Comment, DirectMessage, Report, 
    Notification, Achievement, CharacterAchievement, Saga, 
    Universe, UniverseMessage
)

Player = get_user_model()


# 1. SAGA SERIALIZER (Vem primeiro para o Character conseguir ler)
class SagaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Saga
        fields = ['id', 'author', 'title', 'description', 'created_at']


# 2. CHARACTER SERIALIZER
class CharacterSerializer(serializers.ModelSerializer):
    player_username = serializers.ReadOnlyField(source='player.username')
    player_is_premium = serializers.ReadOnlyField(source='player.is_premium')
    total_followers = serializers.ReadOnlyField()
    total_following = serializers.ReadOnlyField()
    top_followers = serializers.SerializerMethodField()
    
    # Conecta a lista de Sagas no perfil do personagem
    sagas = SagaSerializer(many=True, read_only=True)

    class Meta:
        model = Character
        fields = '__all__'
        read_only_fields = ('player',)

    def get_top_followers(self, obj):
        try:
            followers = obj.followers.all()[:5]
            return [{"id": f.id, "name": f.name, "avatar": f.avatar.url if f.avatar else None} for f in followers]
        except Exception:
            return []


# 3. COMMENT SERIALIZER
class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    
    author_is_alpha_tester = serializers.ReadOnlyField(source='author.is_alpha_tester')
    author_show_alpha_badge = serializers.ReadOnlyField(source='author.show_alpha_badge')
    
    total_likes = serializers.ReadOnlyField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_name', 'author_avatar', 
            'author_is_alpha_tester', 'author_show_alpha_badge',
            'content', 'parent', 'likes', 'total_likes', 'replies', 'created_at'
        ]

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []


# 4. POST SERIALIZER (Com o campo 'saga' adicionado)
class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    author_username = serializers.CharField(source='author.player.username', read_only=True)
    
    author_is_alpha_tester = serializers.ReadOnlyField(source='author.is_alpha_tester')
    author_show_alpha_badge = serializers.ReadOnlyField(source='author.show_alpha_badge')

    total_likes = serializers.ReadOnlyField()
    comments = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'author_username', 'author_avatar', 
            'author_is_alpha_tester', 'author_show_alpha_badge',
            'content', 'image', 'spotify_track_url', 'font_style', 'saga', 
            'likes', 'total_likes', 'comments', 'reactions', 'created_at'
        ]

    def get_comments(self, obj):
        main_comments = obj.comments.filter(parent__isnull=True).order_by('created_at')
        return CommentSerializer(main_comments, many=True).data

    def get_reactions(self, obj): 
        summary = []
        for emj in ['❤️', '🔥', '😡', '👎', '😂', '🎉']:
            count = obj.reactions.filter(emoji=emj).count()
            users_reacted = list(obj.reactions.filter(emoji=emj).values_list('persona_id', flat=True))
            summary.append({'emoji': emj, 'count': count, 'users': users_reacted})
        return summary


# 5. DIRECT MESSAGE SERIALIZER
class DirectMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = DirectMessage
        fields = ['id', 'sender', 'sender_name', 'sender_avatar', 'receiver', 'content', 'image', 'is_read', 'created_at']


# 6. REPORT SERIALIZER
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'


# 7. REGISTER SERIALIZER
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Player.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


# 8. NOTIFICATION SERIALIZER
class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_name', 'sender_avatar', 
            'notification_type', 'post', 'is_read', 'created_at'
        ]


# 9. UNIVERSE SERIALIZERS
class UniverseSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.name')
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Universe
        fields = '__all__'

    def get_member_count(self, obj):
        return obj.members.count()


class UniverseMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = UniverseMessage
        fields = '__all__'

    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            return obj.sender.avatar.url
        return None


# 10. VALIDAÇÃO DE IMAGEM
def validate_secure_image(image):
    max_size = 5 * 1024 * 1024  # 5MB
    if image.size > max_size:
        raise serializers.ValidationError("A imagem é muito pesada! O limite máximo é de 5MB.")
    
    mime_type, _ = mimetypes.guess_type(image.name)
    valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if mime_type not in valid_types:
        raise serializers.ValidationError("Formato de arquivo inválido. Apenas imagens (JPEG, PNG, WEBP, GIF) são permitidas.")
    
    return image