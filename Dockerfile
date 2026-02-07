# Use an official Python base image
FROM python:3.12-slim

# Set environment variables to prevent Python from buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=OrderFlow.settings.prod

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project into the Docker image
COPY . /app/

# Expose the port that Cloud Run will use (but this is optional, just for documentation)
EXPOSE 8080

# Collect static files and run gunicorn on Cloud Run PORT
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn OrderFlow.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120}"]
