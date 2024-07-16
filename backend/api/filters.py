import django_filters
import django_filters.rest_framework as filters
from django.contrib.auth import get_user_model
from recipes.models import Ingredient, Recipe, Tag

User = get_user_model()


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit')


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())

    class Meta:
        model = Recipe
        fields = ('tags', 'author')

    def filter_queryset(self, queryset):
        print("FILTERING")
        tags = self.data.get('tags')
        if tags and tags == "__all__":
            return queryset
        pk_in_kwargs = self.request.resolver_match.kwargs.get('pk')
        if not tags and not pk_in_kwargs:
            return Recipe.objects.none()
        return super().filter_queryset(queryset)
