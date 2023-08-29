FROM python:3.9

WORKDIR /app

RUN pip install gunicorn==20.1.0

COPY ./backend/requirements.txt .

RUN pip install --upgrade pip && pip3 install -r requirements.txt --no-cache-dir

COPY ./backend/ .

COPY ../entrypoint.sh /app/entrypoint.sh
COPY ../data/ /app/data/

CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0.0.0.0:8000" ]