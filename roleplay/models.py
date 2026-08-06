from django.db import models
from django.contrib.auth.models import AbstractUser

class Player(AbstractUser):
    max_characters = models.IntegerField(default=2)
    is_premium = models.BooleanField(default=False)
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
    age = models.CharField(max_length=50, blank=True, null=True)
    bio = models.TextField(blank=True)
    hobbies = models.TextField(blank=True)
    theme_music_url = models.URLField(blank=True, null=True)
    theme_preference = models.CharField(max_length=50, default='dark_default')
    
    followers = models.ManyToManyField('self', symmetrical=False, related_name='following', blank=True)
    
    # NOVO CAMPO: Sistema de Silenciar/Ocultar
    muted_characters = models.ManyToManyField('self', symmetrical=False, related_name='muted_by', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Você (Admin) marca isso como True para quem testou a Pré-Alpha
    is_alpha_tester = models.BooleanField(default=False)
    
    # O usuário controla isso pelo botão de toggle dele
    show_alpha_badge = models.BooleanField(default=True)
    # ================= ECONOMIA E MISSÕES =================
    fl_coins = models.IntegerField(default=150) # Saldo inicial
    
    
    # Trackers para Quests Diárias (Salva a data em que a persona fez a missão)
    last_daily_post = models.DateField(null=True, blank=True)
    last_daily_chat = models.DateField(null=True, blank=True)
    
    # Efeito ativo (Aura da Loja)
    active_effect = models.CharField(max_length=50, blank=True, null=True)

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
    # ➕ ADICIONE ESTA LINHA:
    font_style = models.CharField(max_length=50, default='sans-serif', blank=True, null=True)
    saga = models.ForeignKey('Saga', on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')

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
    # ADICIONE ESTA LINHA:
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)

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
    # ================= SISTEMA DE CONQUISTAS =================

class Achievement(models.Model):
    """ Tabela com todas as conquistas disponíveis no jogo """
    ACHIEVEMENT_TYPES = [
        ('posts', 'Quantidade de Posts'),
        ('messages', 'Mensagens Privadas'),
        ('followers', 'Seguidores Alcançados'),
    ]
    
    title = models.CharField(max_length=100) # Ex: "Escritor Novato"
    description = models.TextField() # Ex: "Faça 50 posts na plataforma"
    coin_reward = models.IntegerField(default=100) # Quantas FL Coins ele ganha
    target_count = models.IntegerField(default=1) # O alvo numérico (ex: 50)
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)

    def __str__(self):
        return f"{self.title} (Recompensa: {self.coin_reward} moedas)"


class CharacterAchievement(models.Model):
    """ Tabela que cruza a Persona com a Conquista para evitar recompensas duplicadas """
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='achievements_unlocked')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    achieved_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Isso garante que uma Persona nunca possa resgatar a mesma conquista duas vezes!
        unique_together = ('character', 'achievement') 

    def __str__(self):
        return f"{self.character.name} completou -> {self.achievement.title}"
class Universe(models.Model):
    NICHO_CHOICES = [
        ('rpg', 'RPG (Fantasia, Ação, etc)'),
        ('fake', 'Fake / Vida Real'),
        ('interagir', 'Interação / Slice of Life'),
        ('outro', 'Outro Nicho'),
    ]

    PRIVACY_CHOICES = [
        ('open', 'Aberto (Qualquer um entra)'),
        ('request', 'Somente com Solicitação'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    rules = models.TextField(blank=True, null=True) # Regras do grupo
    niche = models.CharField(max_length=20, choices=NICHO_CHOICES, default='interagir')
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='open')
    cover_image = models.ImageField(upload_to='universe_covers/', blank=True, null=True)
    
    # Criador/Dono do Universo
    owner = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='owned_universes')
    
    # Membros que fazem parte
    members = models.ManyToManyField(Character, related_name='universes_joined', blank=True)
    
    # Solicitações pendentes (para grupos fechados)
    pending_members = models.ManyToManyField(Character, related_name='universe_requests', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_niche_display()})"
class UniverseMessage(models.Model):
    universe = models.ForeignKey(Universe, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Character, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='universe_chat/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.universe.name}] {self.sender.name}: {self.content[:20]}"
class PostReaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    persona = models.ForeignKey(Character, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)  # Ex: '❤️', '🔥', '😡', '👎', '😂', '🎉'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'persona', 'emoji')
    
# COLOQUE NO FINAL DO SEU models.py

class Saga(models.Model):
    author = models.ForeignKey('Character', on_delete=models.CASCADE, related_name='sagas')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.author.name}"