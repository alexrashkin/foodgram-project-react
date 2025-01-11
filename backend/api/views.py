import logging

from django.db.models import F, Q, Sum
from django.shortcuts import HttpResponse, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipesIngredients,
                            ShoppingCart, Tag)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import Subscription, User

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAdminUserOrReadOnly, IsOwnerAdmin
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeGetSerializer, RecipeSaveSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          TagSerializer, UserSerializer)

logger = logging.getLogger(__name__)


class IngredientsViewset(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    """
    Вьюсет для ингредиентов.
    Позволяет получать список ингредиентов и детали отдельных ингредиентов.
    """

    queryset = Ingredient.objects.all()
    model = Ingredient
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminUserOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None
    filterset_class = IngredientFilter


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Favorite.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user == self.request.user:
            instance.delete()

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            context = {'request': request}
            recipe = get_object_or_404(Recipe, id=pk)
            data = {
                'user': request.user.id,
                'recipe': recipe.id
            }

            serializer = FavoriteSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            deleted_favs = Favorite.objects.filter(
                user=request.user, recipe=recipe).delete()

            if deleted_favs[0] == 0:
                return Response(status=status.HTTP_404_NOT_FOUND)

            return Response(status=status.HTTP_204_NO_CONTENT)


class RecipesViewset(viewsets.ModelViewSet):
    """
    Вьюсет для рецептов.
    Позволяет получать список рецептов, создавать, изменять и удалять рецепты.
    Может добавлять и удалять рецепты из избранного.
    Может генерировать список покупок для рецептов.
    """

    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    ordering = ['-pub_date']
    pagination_class = PageNumberPagination
    filterset_class = RecipeFilter

    def get_queryset(self):
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None and int(is_favorited) == 1:
            return Recipe.objects.filter(favorites__user=self.request.user)

        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        if is_in_shopping_cart is not None and int(is_in_shopping_cart) == 1:
            return Recipe.objects.filter(shopping_cart__user=self.request.user)

        return Recipe.objects.all()

    def perform_create(self, serializer):
        """
        Создает новый рецепт и связывает с
        текущим пользователем как автором.
        """

        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        """
        Возвращает соответствующий сериализатор
        в зависимости от метода запроса.
        """
        if self.action == 'list' or self.action == 'retrieve':
            return RecipeGetSerializer
        return RecipeSaveSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response('Рецепт успешно удален',
                        status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=(IsOwnerAdmin,))
    def favorites(self, request, pk):
        """
        Добавляет или удаляет рецепт из избранного для пользователя.
        POST - добавление в избранное, DELETE - удаление из избранного.
        """

        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
                return Response({'detail': 'Рецепт уже добавлен в избранное.'},
                                status=status.HTTP_400_BAD_REQUEST)
            new_fav = Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = FavoriteSerializer(new_fav,
                                            context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            old_fav = get_object_or_404(Favorite,
                                        user=request.user,
                                        recipe=recipe)
            self.perform_destroy(old_fav)
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise MethodNotAllowed(request.method)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        recipe = self.get_object()

        if request.method == 'POST':
            new_cart_item, created = ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe)

            if not created:
                return Response(
                    {'detail': 'Рецепт уже добавлен в список покупок.'},
                    status=status.HTTP_400_BAD_REQUEST)

            serializer = ShoppingCartSerializer(new_cart_item,
                                                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            cart_item = get_object_or_404(ShoppingCart, user=request.user,
                                          recipe=recipe)
            cart_item.delete()
            return Response(
                {'detail': 'Рецепт успешно удален из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """
        Генерирует список покупок для рецептов пользователя
        и предоставляет его для скачивания.
        """

        recipes = Recipe.objects.filter(shopping_cart__user=request.user)
        shopping_cart = RecipesIngredients.objects.filter(
            recipe__in=recipes).values(
            name=F('ingredient__name'),
            units=F('ingredient__measurement_unit')).order_by(
            'ingredient__name').annotate(total=Sum('amount'))
        text = 'Список покупок: \n\n'
        ingr_list = []
        for recipe in shopping_cart:
            ingr_list.append(recipe)
        for i in ingr_list:
            text += f'{i["name"]}: {i["total"]}, {i["units"]}.\n'
        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = ('attachment;'
                                           'filename="shopping_cart.txt"')
        return response


class TagViewset(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """
    Вьюсет для тегов.
    Позволяет получать список тегов и детали отдельных тегов.
    """

    queryset = Tag.objects.filter(~Q(color="srv"))
    serializer_class = TagSerializer
    permission_classes = (IsAdminUserOrReadOnly,)
    pagination_class = None


class UserViewset(UserViewSet):
    """
    Вьюсет для работы с пользователем.
    Позволяет получать список пользователей и детали отдельных пользователей.
    Может добавлять и удалять подписки на пользователей.
    Может получать список подписок пользователя.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        """
        Добавляет или удаляет подписку на пользователя.
        POST - добавление подписки, DELETE - удаление подписки.
        """

        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if request.user == author:
                return Response({
                    'detail': 'Вы не можете подписаться на себя'
                }, status=status.HTTP_400_BAD_REQUEST)

            if Subscription.objects.filter(user=user, author=author).exists():
                return Response({
                    'detail': 'Подписка уже существует'
                }, status=status.HTTP_400_BAD_REQUEST)

            new_sub = Subscription.objects.create(user=user, author=author)
            serializer = SubscribeSerializer(
                new_sub, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            instance = get_object_or_404(
                Subscription, user=user, author=author
            )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)

        raise MethodNotAllowed(request.method)

    @action(methods=['GET'], detail=False,
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """
        Получает список подписок пользователя.
        """

        user = request.user
        queryset = Subscription.objects.filter(user=user)
        page = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            page,
            many=True,
            context={'request': request}
        )

        subscriptions_data = serializer.data

        results = []
        for subscription in subscriptions_data:
            author = User.objects.get(id=subscription['author'])
            recipes = Recipe.objects.filter(author=author)\
                            .order_by('-pub_date')
            recipe_data = []
            for recipe in recipes:
                recipe_data.append({
                    "id": recipe.id,
                    "name": recipe.name,
                    "image": recipe.image.url,
                    "cooking_time": recipe.cooking_time,
                })

            result_entry = {
                "email": author.email,
                "id": author.id,
                "username": author.username,
                "first_name": author.first_name,
                "last_name": author.last_name,
                "is_subscribed": True,
                "recipes": recipe_data,
                "recipes_count": recipes.count(),
            }

            results.append(result_entry)

        response_data = {
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "results": results,
        }

        return Response(response_data, status=status.HTTP_200_OK)
