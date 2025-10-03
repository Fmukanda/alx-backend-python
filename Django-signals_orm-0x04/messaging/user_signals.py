from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@receiver(pre_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """
    Log user deletion for audit purposes
    """
    logger.info(f"User {instance.username} (ID: {instance.id}) is being deleted")

@receiver(pre_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """
    Custom cleanup logic before user deletion
    This runs before CASCADE deletions, allowing custom logging or archiving
    """
    try:
        # Log statistics before deletion (for analytics)
        sent_messages_count = instance.sent_messages.count()
        received_messages_count = instance.received_messages.count()
        notifications_count = instance.notifications.count()
        edits_count = instance.message_edits.count()
        
        logger.info(
            f"User {instance.username} deletion stats: "
            f"Sent messages: {sent_messages_count}, "
            f"Received messages: {received_messages_count}, "
            f"Notifications: {notifications_count}, "
            f"Edits: {edits_count}"
        )
        
        # Archive important data before deletion (optional)
        # archive_user_data(instance)
        
    except Exception as e:
        logger.error(f"Error during user data cleanup for {instance.username}: {str(e)}")

@receiver(post_delete, sender=User)
def post_user_deletion_cleanup(sender, instance, **kwargs):
    """
    Additional cleanup after user is deleted
    """
    try:
        # Clean up any cached data related to the user
        user_cache_keys = [
            f"user_{instance.id}_unread_notifications",
            f"user_{instance.id}_profile",
            f"user_{instance.id}_messages",
        ]
        
        for key in user_cache_keys:
            cache.delete(key)
        
        logger.info(f"Post-deletion cleanup completed for user {instance.username}")
        
    except Exception as e:
        logger.error(f"Error during post-deletion cleanup: {str(e)}")