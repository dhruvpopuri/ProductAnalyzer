#!/bin/sh

if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Make migrations and migrate the database.
echo "Making migrations and migrating the database. "
python ProductAnalyzer/manage.py makemigrations --noinput
python ProductAnalyzer/manage.py migrate --noinput
python ProductAnalyzer/manage.py collectstatic --noinput

# Start Gunicorn
exec gunicorn ProductAnalyzer.ProductAnalyzer.wsgi:application --bind 0.0.0.0:8000 --workers=4 --timeout=3600

exec "$@"