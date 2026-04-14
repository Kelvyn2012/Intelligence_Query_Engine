release: python manage.py collectstatic --noinput && python manage.py migrate
web: gunicorn genderize_project.wsgi --bind 0.0.0.0:$PORT --log-level debug --capture-output