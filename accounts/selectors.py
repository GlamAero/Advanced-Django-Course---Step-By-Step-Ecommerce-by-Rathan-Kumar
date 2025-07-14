from .models import UserActivity
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone

def get_suspicious_activities(threshold=3, hours=1):
    """Get IP addresses with suspicious login activity patterns"""
    cutoff = timezone.now() - timedelta(hours=hours)
    return (
        UserActivity.objects
        .filter(timestamp__gte=cutoff, activity_type='login')
        .values('ip_address')
        .annotate(attempts=Count('ip_address'))
        .filter(attempts__gte=threshold)
    )

def get_user_activity_summary(user):
    """Get security summary for user profile"""
    return {
        'last_login': (
            UserActivity.objects
            .filter(user=user, activity_type='login')
            .order_by('-timestamp')
            .first()
        ),
        'recent_activities': (
            UserActivity.objects
            .filter(user=user)
            .order_by('-timestamp')[:5]
        ),
        'password_changed': (
            UserActivity.objects
            .filter(user=user, activity_type='password_reset')
            .exists()
        )
    }