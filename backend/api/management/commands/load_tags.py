from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        data = [
            {'name': 'Завтрак', 'color': '#FF5733', 'slug': 'breakfast'},
            {'name': 'Обед', 'color': '#33FF57', 'slug': 'dinner'},
            {'name': 'Ужин', 'color': '#5733FF', 'slug': 'supper'}]
        Tag.objects.bulk_create(Tag(**tag) for tag in data)
        self.stdout.write(self.style.SUCCESS('Теги успешно загружены!'))
