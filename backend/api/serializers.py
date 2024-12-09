import base64
import logging

from django.core.files.base import ContentFile
from recipes.models import (Favorite, Ingredient, Recipe, RecipesIngredients,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Subscription, User

logger = logging.getLogger(__name__)


class Base64ImageField(serializers.ImageField):
    """
    Кастомное поле для сериализации изображения в формате base64.
    """

    def to_internal_value(self, data):
        """
        Преобразует строку данных изображения в объект ContentFile.
        """
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользовательской модели."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'password', 'is_subscribed')

    def create(self, validated_data):
        """
        Создает и сохраняет нового пользователя.
        """
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def get_is_subscribed(self, obj):
        """
        Возвращает True, если текущий пользователь подписан на автора.
        """
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=obj).exists()

    def to_representation(self, instance):
        """Функция для измения представления при GET и POST запросах."""
        instance = super().to_representation(instance)
        if self.context.get('request').method == 'POST':
            instance.pop('is_subscribed')
        return instance


class GetUserSubscribesSerializer(UserSerializer):
    """
    Сериализатор для получения информации о подписках пользователя.
    """
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для изменения пароля пользователя.
    """
    model = User
    new_password = serializers.CharField(max_length=150, required=True)
    current_password = serializers.CharField(max_length=150, required=True)

    def validate_current_password(self, value):
        """
        Проверяет текущий пароль пользователя перед изменением пароля.
        """
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный пароль!")
        return value


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class TagRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для связи тега с рецептом."""
    class Meta:
        fields = ('id',)
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели связи рецепта и ингредиента с количеством."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
        write_only=True
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipesIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSaveSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления и обновления рецепта.
    """

    author = UserSerializer(
        read_only=True, default=serializers.CurrentUserDefault()
    )
    ingredients = IngredientRecipeSerializer(
        many=True, source='recipes_ingredients'
    )
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    def validate(self, data):
        """
        Проверяет данные рецепта перед созданием или обновлением.
        """
        ingredients_data = data.get('recipes_ingredients')
        ingredients_set = set()

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('ingredient')
            amount = ingredient_data.get('amount')

            if not ingredient:
                raise serializers.ValidationError(
                    'Ингредиент не указан'
                )

            if amount is not None and amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиентов не может быть меньше одного'
                )

            ingredient_tuple = (ingredient.id, amount)
            if ingredient_tuple in ingredients_set:
                raise serializers.ValidationError(
                    'В рецепт нельзя добавлять два одинаковых ингредиента'
                )
            ingredients_set.add(ingredient_tuple)

        return data

    def create(self, validated_data):
        """Создаёт новый рецепт."""

        ingredients_data = validated_data.pop('recipes_ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        ingredients_to_create = []
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('ingredient')
            amount = ingredient_data.get('amount')
            ingredients_to_create.append(
                RecipesIngredients(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
            )
        RecipesIngredients.objects.bulk_create(ingredients_to_create)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет существующий рецепт."""

        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipes_ingredients')
        validated_data.pop('author', None)
        RecipesIngredients.objects.filter(recipe=instance).delete()
        instance.tags.set(tags)
        self.get_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def get_ingredients(self, recipe, ingredients_data):
        """Получает ингредиенты для рецепта."""

        ingredients_to_create = []
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('ingredient')
            amount = ingredient_data.get('amount')
            ingredients_to_create.append(
                RecipesIngredients(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
            )
        RecipesIngredients.objects.bulk_create(ingredients_to_create)
        return recipe

    def to_representation(self, instance):
        """
        Преобразует экземпляр модели Recipe в сериализованные данные.
        """
        request = self.context.get('request')

        if request.user.is_authenticated:
            is_favorited = Favorite.objects.filter(
                user=request.user, recipe=instance).exists()
            instance.is_favorited = is_favorited

        return super().to_representation(instance)

    class Meta:
        model = Recipe
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['author', 'name'],
                message='Рецепт с таким названием уже добавлен')
        ]
        fields = '__all__'
        read_only_fields = ('author',)


class RecipeGetSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получения информации о рецепте.
    """

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(
        many=True, read_only=True, source='recipes_ingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    def get_is_favorited(self, obj):
        """
        Проверяет, добавлен ли рецепт в избранное у текущего пользователя.
        """
        request = self.context.get('request')
        return request.user.is_authenticated and Favorite.objects.filter(
            user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """
        Проверяет, добавлен ли рецепт в список покупок у текущего пользователя.
        """
        request = self.context.get('request')
        return request.user.is_authenticated and ShoppingCart.objects.filter(
            user=request.user, recipe=obj).exists()

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('id', 'author',)


class UserSubscribeControlSerializer(UserSerializer):
    """Сериализатор для управления подпиской/отпиской пользователя."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')
        read_only_fields = ('email', 'username', 'first_name', 'last_name',
                            'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, obj):
        """
        Возвращает список рецептов пользователя с опциональным ограничением
        по количеству.
        """
        request = self.context.get('request')
        recipes_limit = None
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = obj.recipes.all()[:int(recipes_limit)]
        return RecipeGetSerializer(recipes, many=True,
                                   context={'request': request}).data

    def get_recipes_count(self, obj):
        """
        Возвращает общее количество рецептов пользователя.
        """
        return obj.recipes.count()


class SubscribeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с подпиской на пользователя.
    """

    class Meta:
        model = Subscription
        fields = ('id', 'author', 'user')
        read_only_fields = fields

    def validate(self, data):
        """
        Проверяет, можно ли подписаться на пользователя,
        иначе вызывает исключение.
        """
        author = self.context['author']
        user = self.context['request'].user
        if (
            author == user
            or Subscription.objects.filter(
                author=author,
                user=user
            ).exists()
        ):
            raise serializers.ValidationError(
                'Нельзя подписаться на этого пользователя!'
            )
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для работы со списком покупок."""

    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок'
            )
        ]

    def to_representation(self, instance):
        """
        Преобразует экземпляр модели ShoppingCart в сериализованные данные.
        """
        request = self.context.get('request')
        return RecipeSaveSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с избранными рецептами."""

    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное'
            )
        ]

    def to_representation(self, instance):
        """
        Преобразует экземпляр модели Favorite в сериализованные данные.
        """
        request = self.context.get('request')
        return RecipeSaveSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class RecipeFollowSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
