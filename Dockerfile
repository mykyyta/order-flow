# Use an official Python base image
FROM python:3.12-slim

# Set environment variables to prevent Python from buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y gcc libpq-dev

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project into the Docker image
COPY . /app/

# Expose the port that Cloud Run will use (but this is optional, just for documentation)
EXPOSE 8080

# Run the Django server on Cloud Run PORT
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:${PORT}"]
