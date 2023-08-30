from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import IngredientsViewset, RecipesViewset, TagViewset, FavoriteViewSet

router = DefaultRouter()
router.register('recipes', RecipesViewset, basename='recipes')
router.register('ingredients', IngredientsViewset, basename='ingredients')
router.register('tags', TagViewset, basename='tags')
router.register('favorite', FavoriteViewSet, basename='favorite')

urlpatterns = [
    path('', include(router.urls)),
]
