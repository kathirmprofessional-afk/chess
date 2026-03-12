import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_tournament.settings')
django.setup()

from accounts.models import User

# Add users if they don't exist
for username in ['alice', 'bob']:
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username=username, password='testpass123', email=f'{username}@example.com')
        print(f'Created user {username}')
