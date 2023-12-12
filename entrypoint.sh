#!/bin/bash

# python manage.py flush --no-input

python manage.py makemigrations

python manage.py migrate

# python manage.py load_ingredients
# python manage.py load_tags

gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000

cp -r /app/backend/collected_static/. /backend_static/static/

source load_env.sh
