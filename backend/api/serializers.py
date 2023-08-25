import base64

from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, Recipe, RecipesIngredients,
                            ShoppingList, Tag)
from users.models import Subscription, User


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
        write_only_fields = ('password',)
        read_only_fields = ('id',)

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
        Возвращает True, если текущий пользователь подписан на пользователя obj.
        """
        request = self.context.get('request')
        if request and request.user.is_not_authenticated:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()
    
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
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели связи рецепта и ингредиента с количеством."""

    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.ReadOnlyField()

    class Meta:
        model = RecipesIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount')



class RecipeSaveSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления и обновления рецепта.
    """

    author = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    ingredients = IngredientRecipeSerializer(
        many=True, source='recipe_ingredients'
    )
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['author', 'name'],
                message='Рецепт с таким названием уже добавлен')
        ]
        fields = ('author', 'ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time')
        
    def validate(self, data):
        """
        Проверяет данные рецепта перед созданием или обновлением.
        """
        ingredients_list = []
        for ingredient in data.get('recipe_ingredients'):
            amount = ingredient.get('amount')
            if amount is not None and amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиентов не может быть меньше 1'
                )
            ingredients_list.append(ingredient.get('id'))
        if len(set(ingredients_list)) != len(ingredients_list):
            raise serializers.ValidationError(
                'В рецепт нельзя добавлять два одинаковых ингредиента'
            )
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(author=request.user, **validated_data)
        recipe.tags.set(tags)
        self.get_ingredients(recipe, ingredients)

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipe_ingredients')

        RecipesIngredients.objects.filter(recipe=instance).delete()

        instance.tags.set(tags)
        self.get_ingredients(instance, ingredients)

        return super().update(instance, validated_data)
    

class RecipeGetSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получения информации о рецепте.
    """

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientRecipeSerializer(many=True, read_only=True, source='recipe_ingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)
    
    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, obj):
        """
        Проверяет, добавлен ли рецепт в избранное у текущего пользователя.
        """
        request = self.context.get('request')
        return request.user.is_authenticated and Favorite.objects.filter(
            user=request.user, recipe__id=obj.id).exists()
    
    def get_is_in_shopping_cart(self, obj):
        """
        Проверяет, добавлен ли рецепт в список покупок у текущего пользователя.
        """
        request = self.context.get('request')
        return request.user.is_authenticated and ShoppingList.objects.filter(
            user=request.user, recipe__id=obj.id).exists()

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
        Возвращает список рецептов пользователя с опциональным ограничением по количеству.
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
        Проверяет, можно ли подписаться на пользователя, иначе вызывает исключение.
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


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для работы со списком покупок."""

    class Meta:
        model = ShoppingList
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingList.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок'
            )
        ]

    def to_representation(self, instance):
        """
        Преобразует экземпляр модели ShoppingList в сериализованные данные.
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
       