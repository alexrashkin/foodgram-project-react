from .serializers import (UserSerializer, TagSerializer,
                            IngredientSerializer, RecipeSaveSerializer,
                            RecipeSaveSerializer,
                            RecipeGetSerializer,
                            SubscribeSerializer,
                            FavoriteSerializer
                            )
from django.db.models import F, Sum
from djoser.views import UserViewSet
from django.shortcuts import HttpResponse, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (RecipesIngredients, Favorite, ShoppingList, Recipe,
                            Ingredient, Tag)
from users.models import User, Subscription
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .permissions import (
    IsAdminOrAuthorOrReadOnly, IsAdminUserOrReadOnly, IsOwnerAdmin
)
from rest_framework.response import Response


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


class RecipesViewset(viewsets.ModelViewSet):
    """
    Вьюсет для рецептов.
    Позволяет получать список рецептов, создавать, изменять и удалять рецепты.
    Может добавлять и удалять рецепты из избранного.
    Может генерировать список покупок для рецептов.
    """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSaveSerializer
    permission_classes = (IsAdminOrAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    ordering = ['-id']
    pagination_class = PageNumberPagination

    def perform_create(self, serializer):
        """
        Создает новый рецепт и связывает его с текущим пользователем как автором.
        """

        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        """
        Определяет класс сериализатора на основе действия.
        Использует RecipeSaveSerializer для действий create и partial_update,
        и RecipeGetSerializer для остальных действий.
        """

        if self.action in ['create', 'partial_update']:
            return RecipeSaveSerializer
        return RecipeGetSerializer

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=(IsOwnerAdmin,))
    def favorite(self, request, id):
        """
        Добавляет или удаляет рецепт из избранного для пользователя.
        Метод POST - добавление в избранное, DELETE - удаление из избранного.
        """

        recipe = get_object_or_404(Recipe, id=id)
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
    
    @action(detail=False, methods=['get'],
            permission_classes=(IsOwnerAdmin,))
    def download_shopping_list(self, request):
        """
        Генерирует список покупок для рецептов пользователя и предоставляет его для скачивания.
        """

        shopping_list = RecipesIngredients.objects.filter(
            recipe__shopping_cart__user=request.user).values(
            name=F('ingredient__name'),
            units=F('ingredient__measurement_unit')).order_by(
            'ingredient__name').annotate(total=Sum('amount'))
        text = 'Список покупок: \n\n'
        ingr_list = []
        for recipe in shopping_list:
            ingr_list.append(recipe)
        for i in ingr_list:
            text += f'{i["name"]}: {i["total"]}, {i["units"]}.\n'
        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = ('attachment;'
                                           'filename="shopping_list.txt"')
        return response


class TagViewset(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """
    Вьюсет для тегов.
    Позволяет получать список тегов и детали отдельных тегов.
    """

    queryset = Tag.objects.all()
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
    
    @action(methods=['post', 'delete'], detail=True,
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        """
        Добавляет или удаляет подписку на пользователя.
        Метод POST - добавление подписки, DELETE - удаление подписки.
        """

        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if Subscription.objects.filter(
                user_id=request.user.id, author_id=author.id).exists() or request.user == author:
                return Response({
                    'detail': 'Подписка уже есть или Вы пытаетесь подписаться на себя'
                }, status=status.HTTP_400_BAD_REQUEST)
            new_sub = Subscription.objects.create(user=request.user, author=author)
            serializer = SubscribeSerializer(new_sub,
                                         context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = get_object_or_404(
                Subscription, user=request.user, author=author
            )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise MethodNotAllowed(request.method)

    @action(methods=['get'], detail=False,
            serializer_class=SubscribeSerializer,
            permission_classes=(IsOwnerAdmin,))
    def subscriptions(self, request):
        """
        Получает список подписок пользователя.
        """

        queryset = Subscription.objects.filter(user_id=request.user.id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)
