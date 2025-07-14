import logging
from .models import UserActivity

logger = logging.getLogger(__name__)

def log_activity(user, action, request):
    try:
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate to 500 chars
        UserActivity.objects.create(
            user=user,
            activity_type=action,
            ip_address=get_client_ip(request),
            user_agent=user_agent
        )
        logger.info(f"Activity: {action} by {user.email} from IP {get_client_ip(request)}")
    except Exception as e:
        logger.error(f"Failed to log activity for {user.email}: {e}")

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
