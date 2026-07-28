from django.db import models
from django.contrib.auth.models import AbstractUser

class Player(AbstractUser):
    """
    Conta do usuário real (Aquele que gerencia as máscaras).
    """
    max_characters = models.IntegerField(default=3)

    def __str__(self):
        return self.username

class Character(models.Model):
    """
    A 'Máscara' / Perfil Fake. 
    Contém todos os dados sociais, de lore e configurações de UI.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='characters')
    
    # Identidade Básica
    name = models.CharField(max_length=150, help_text="Ex: Fangsblood")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    
    # Inclusão e Detalhes Pessoais
    pronouns = models.CharField(max_length=50, blank=True, help_text="Ex: Ele/Dele, Ela/Dela, Elu/Delu")
    sexuality = models.CharField(max_length=100, blank=True, help_text="Ex: Bissexual, Pansexual, Assexual")
    
    # Lore (A "Identidade" na rede)
    species = models.CharField(max_length=100, blank=True, help_text="Raça. Ex: Hellhound, Humano, Elfo")
    location = models.CharField(max_length=150, blank=True, help_text="Onde mora.")
    age = models.CharField(max_length=50, blank=True)
    
    # Personalidade e Gostos
    bio = models.TextField(blank=True)
    hobbies = models.TextField(blank=True)
    theme_music_url = models.URLField(blank=True, null=True)
    
    # Customização de Interface (O Tema)
    theme_preference = models.CharField(
        max_length=50, 
        default='dark_default', 
        help_text="Chave de cor que o frontend usará (ex: 'pink_diamond', 'azul_translucido')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    author = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post de {self.author.name}"

class DirectMessage(models.Model):
    sender = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"De {self.sender.name} para {self.receiver.name}"
