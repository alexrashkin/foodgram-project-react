# Проект «Фудграм»
# Описание
На этом сайте пользователи могут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Пользователям сайта также доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

Стек: Python3, Django3, Django REST framework, React, PostgreSQL, gunicorn, nginx, Яндекс.Облако

# Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/alexrashkin/foodgram-project-react.git
cd foodgram-project-react
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv env
```

* Если у вас Linux/macOS

    ```
    source env/bin/activate
    ```

* Если у вас Windows

    ```
    source env/scripts/activate
    ```

```
python3 -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Выполнить миграции:

```
python3 manage.py migrate
```

Запустить проект:

```
python3 manage.py runserver
```

Над проектом работали: 
- Backend - https://github.com/alexrashkin
- Frontend - https://github.com/yandex-praktikum/foodgram-project-react