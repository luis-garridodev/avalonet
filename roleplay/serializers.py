from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Player, Character, Post, Comment, DirectMessage, Report
from .models import Player, Character, Post, Comment, DirectMessage, Report, Notification

Player = get_user_model()

class CharacterSerializer(serializers.ModelSerializer):
    total_followers = serializers.ReadOnlyField()
    total_following = serializers.ReadOnlyField()

    class Meta:
        model = Character
        fields = [
            'id', 'player', 'name', 'avatar', 'cover_photo', 
            'pronouns', 'sexuality', 'species', 'location', 'age', 
            'bio', 'hobbies', 'theme_music_url', 'theme_preference',
            'followers', 'following', 'total_followers', 'total_following', 
            'created_at', 'is_active'
        ]
        read_only_fields = ('player',)

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    total_likes = serializers.ReadOnlyField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_name', 'author_avatar', 'content', 'parent', 'likes', 'total_likes', 'replies', 'created_at']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []

class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.name')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)
    total_likes = serializers.ReadOnlyField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'author_avatar', 
            'content', 'image', 'spotify_track_url', 
            'likes', 'total_likes', 'comments', 'created_at'
        ]

    def get_comments(self, obj):
        main_comments = obj.comments.filter(parent__isnull=True).order_by('created_at')
        return CommentSerializer(main_comments, many=True).data

class DirectMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = DirectMessage
        fields = ['id', 'sender', 'sender_name', 'sender_avatar', 'receiver', 'content', 'is_read', 'created_at']

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

# Serializer para Cadastrar novos Jogadores
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Player.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user
class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_name', 'sender_avatar', 
            'notification_type', 'post', 'is_read', 'created_at'
        ]