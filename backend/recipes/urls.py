from django.urls import include, path
from rest_framework.routers import DefaultRouter


from api.views import (
     IngredientsViewset,
     RecipesViewset,
     TagViewset,
)

router = DefaultRouter()
router.register('recipes', RecipesViewset, basename='recipes')
router.register('ingredients', IngredientsViewset, basename='ingredients')
router.register('tags', TagViewset, basename='tags')

urlpatterns = [
    path('api/recipes/download_shopping_cart/',
     RecipesViewset.as_view({'get': 'download_shopping_cart'}), name='download'),
    path('', include(router.urls)),
    path('recipes/<int:id>/', RecipesViewset.as_view({'get': 'retrieve', 'put': 'update'}), name='recipe-detail'),
    path('api/recipes/favorite/', RecipesViewset.as_view({'post': 'favorite'}), name='recipe-favorite'),
]
