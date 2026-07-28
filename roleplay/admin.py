from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Player, Character, Post, DirectMessage

# Registrando o nosso Player customizado
admin.site.register(Player, UserAdmin)

# Registrando as máscaras e interações do RPG
admin.site.register(Character)
admin.site.register(Post)
admin.site.register(DirectMessage)