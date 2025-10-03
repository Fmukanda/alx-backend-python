from django.core.cache import cache
from .models import Message

def unread_notifications(request):
    """Add unread notifications count to all templates"""
    if request.user.is_authenticated:
        cache_key = f"user_{request.user.id}_unread_notifications"
        unread_count = cache.get(cache_key)
        
        if unread_count is None:
            unread_count = Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
            cache.set(cache_key, unread_count, 300)
        
        return {
            'unread_notifications_count': unread_count,
        }
    return {'unread_notifications_count': 0}

def unread_messages_count(request):
    """Add unread messages count to all templates"""
    if request.user.is_authenticated:
        cache_key = f"user_{request.user.id}_unread_count"
        unread_count = cache.get(cache_key)
        
        if unread_count is None:
            # Use the custom manager for optimized count
            unread_count = Message.unread_objects.unread_count_for_user(request.user)
            cache.set(cache_key, unread_count, 60)  # Cache for 1 minute
        
        return {
            'unread_messages_count': unread_count,
        }
    return {'unread_messages_count': 0}