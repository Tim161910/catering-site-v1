#!/usr/bin/env bash
python manage.py migrate
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.filter(username='bamboo3').exists():
    print("Superuser bamboo3 already exists")
else:
    User.objects.create_superuser('bamboo3', 'admin@test.com', 'TempPass123')
    print("Superuser bamboo3 created successfully")
EOF