from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (FavoriteViewSet, IngredientsViewset, RecipesViewset,
                    TagViewset, UserViewset)

app_name = 'api'

router = DefaultRouter()

router.register('recipes', RecipesViewset, basename='recipes')
router.register('ingredients', IngredientsViewset, basename='ingredients')
router.register('tags', TagViewset, basename='tags')
router.register('users', UserViewset, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('recipes/<int:pk>/shopping_cart/',
         RecipesViewset.as_view({
             'post': 'shopping_cart',
             'delete': 'shopping_cart'
         }), name='shopping_cart'),
    path('recipes/<int:pk>/favorite/',
         FavoriteViewSet.as_view({
             'post': 'favorite',
             'delete': 'favorite'
         }), name='favorite'),
]
