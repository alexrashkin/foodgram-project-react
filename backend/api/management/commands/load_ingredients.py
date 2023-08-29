import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient


class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **options):
        file_dir = '/home/sanya/foodgram-project-react/data'

        if not os.path.exists(file_dir):
            file_dir = '/app/data'

        with open(os.path.join(file_dir, 'ingredients.csv'), 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                if len(row) == 2:
                    name, measurement_unit = row
                    ingredient, created = Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit,
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created ingredient: {name}, {measurement_unit}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'Ingredient already exists: {name}, {measurement_unit}'))
