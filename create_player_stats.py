#!/usr/bin/env python
"""
Script to create PlayerStats for existing users who don't have them
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import User, PlayerStats

def create_missing_player_stats():
    # Get all users without PlayerStats
    users_without_stats = User.objects.filter(stats__isnull=True)
    
    created_count = 0
    for user in users_without_stats:
        stats, created = PlayerStats.objects.get_or_create(user=user)
        if created:
            print(f'Created PlayerStats for {user.username}')
            created_count += 1
        else:
            print(f'PlayerStats already exists for {user.username}')
    
    print(f'\nSummary:')
    print(f'Total users: {User.objects.count()}')
    print(f'Newly created PlayerStats: {created_count}')
    print(f'Total PlayerStats: {PlayerStats.objects.count()}')

if __name__ == '__main__':
    create_missing_player_stats()