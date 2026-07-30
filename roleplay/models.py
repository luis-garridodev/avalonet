from django.db import models
from django.contrib.auth.models import AbstractUser

class Player(AbstractUser):
    max_characters = models.IntegerField(default=3)

    def __str__(self):
        return self.username


class Character(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    pronouns = models.CharField(max_length=50, blank=True)
    sexuality = models.CharField(max_length=100, blank=True)
    species = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    age = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    hobbies = models.TextField(blank=True)
    theme_music_url = models.URLField(blank=True, null=True)
    theme_preference = models.CharField(max_length=50, default='dark_default')
    
    followers = models.ManyToManyField('self', symmetrical=False, related_name='following', blank=True)
    
    # NOVO CAMPO: Sistema de Silenciar/Ocultar
    muted_characters = models.ManyToManyField('self', symmetrical=False, related_name='muted_by', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
        
    @property
    def total_followers(self):
        return self.followers.count()
        
    @property
    def total_following(self):
        return self.following.count()


class Post(models.Model):
    author = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    spotify_track_url = models.CharField(max_length=255, blank=True, null=True)
    likes = models.ManyToManyField(Character, related_name='liked_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post de {self.author.name}"

    @property
    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Character, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    likes = models.ManyToManyField(Character, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.name} on Post {self.post.id}"
        
    @property
    def total_likes(self):
        return self.likes.count()


class Report(models.Model):
    reporter = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='reports_made')
    reported_post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    reported_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = "Post" if self.reported_post else "Comentário"
        return f"Denúncia de {self.reporter.name} em um {target}"


class DirectMessage(models.Model):
    sender = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"De {self.sender.name} para {self.receiver.name}"

class Notification(models.Model):
    TYPES = (
        ('follow', 'Começou a seguir você'),
        ('like_post', 'Curtiu sua publicação'),
        ('like_comment', 'Curtiu seu comentário'),
        ('comment', 'Comentou na sua publicação'),
    )
    recipient = models.ForeignKey(Character, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(Character, related_name='sent_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=TYPES)
    
    # Link opcional para o post (para a pessoa clicar e ir direto ver a curtida/comentário)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.name} -> {self.recipient.name} ({self.notification_type})"
