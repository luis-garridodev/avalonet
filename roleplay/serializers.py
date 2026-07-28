from rest_framework import serializers
from .models import Character, Post

class CharacterSerializer(serializers.ModelSerializer):
    # O Player (você) não será exposto nos dados públicos por segurança
    class Meta:
        model = Character
        fields = [
            'id', 'name', 'avatar', 'cover_photo', 'pronouns', 'sexuality',
            'species', 'location', 'age', 'bio', 'hobbies', 
            'theme_music_url', 'theme_preference', 'created_at'
        ]

class PostSerializer(serializers.ModelSerializer):
    # Trazemos informações resumidas do autor do post (a Máscara)
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'author_avatar', 
            'content', 'media_url', 'created_at'
        ]