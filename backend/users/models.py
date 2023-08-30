from django.contrib.auth.models import AbstractUser
from django.db import models

from .validators import validate_username


class User(AbstractUser):
    """Создание модели пользователя."""

    USER = 'user'
    ADMIN = 'admin'

    CHOICES = (
        (USER, 'Пользователь'),
        (ADMIN, 'Администратор'),
    )
    role = models.CharField(
        max_length=50,
        choices=CHOICES,
        blank=False,
        default=USER,
        verbose_name='Роль'
    )
    email = models.EmailField(
        max_length=254,
        unique=True,
        blank=False,
        verbose_name='Электронная почта'
    )
    username = models.CharField(
        validators=(validate_username, ),
        max_length=150,
        unique=True,
        blank=False,
        null=False,
        verbose_name='Никнейм'
    )
    first_name = models.CharField(
        max_length=150,
        blank=False,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        blank=False,
        verbose_name='Фамилия'
    )
    password = models.CharField(
        max_length=150,
        verbose_name="Пароль"
    )
    is_subscribed = models.BooleanField(
        default=False,
        verbose_name="Подписка на пользователя"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username
    
    @property
    def is_user(self):
        return self.role == self.USER

    @property
    def is_admin(self):
        return self.role == self. ADMIN or self.is_superuser

class Subscription(models.Model):
    """Создание модели подписки."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="Подписчик"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_author",
        verbose_name="Автор",
        default=None
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            )
        ]
    
    def __str__(self):
        return f'Пользователь: {self.user.username} подписан на {self.author.username}'
