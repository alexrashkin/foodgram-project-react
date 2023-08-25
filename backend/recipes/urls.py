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
    path('recipes/download_shopping_list/',
         RecipesViewset.as_view(
          {'get': 'download_shopping_list'}), name='download'),
    path('', include(router.urls)),
]
