FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the data directory exists for the SQLite database
RUN mkdir -p /app/data

# Use a placeholder key only for the build-time collectstatic step
RUN DJANGO_SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 --workers 3 carbon_calculator.wsgi:application"]
