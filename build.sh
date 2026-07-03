#!/usr/bin/env bash 
python manage.py migrate 
"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('bamboo3', 'admin@test.com', 'TempPass123')" | python manage.py shell 
