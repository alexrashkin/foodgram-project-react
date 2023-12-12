from api.views import (FavoriteViewSet, IngredientsViewset, RecipesViewset,
                       TagViewset)
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('recipes', RecipesViewset, basename='recipes')
router.register('ingredients', IngredientsViewset, basename='ingredients')
router.register('tags', TagViewset, basename='tags')
router.register('favorite', FavoriteViewSet, basename='favorite')

urlpatterns = [
    path('', include(router.urls)),
]
