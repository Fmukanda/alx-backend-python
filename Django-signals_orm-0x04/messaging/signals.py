from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Message, Notification, MessageHistory

@receiver(pre_save, sender=Message)
def log_message_edit(sender, instance, **kwargs):
    """
    Signal to capture message content before it's edited and save to MessageHistory
    """
    if instance.pk:
        try:
            old_message = Message.objects.get(pk=instance.pk)
            if old_message.content != instance.content:
                MessageHistory.objects.create(
                    message=old_message,
                    old_content=old_message.content,
                    new_content=instance.content,
                    edited_by=instance.sender,
                    edit_reason=getattr(instance, '_edit_reason', None)
                )
        except Message.DoesNotExist:
            pass

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Create notifications for new messages and replies
    """
    if created:
        notification_type = 'reply' if instance.parent_message else 'message'
        target_user = instance.receiver
        
        if instance.parent_message:
            title = f"New reply from {instance.sender.username}"
            message_content = f"New reply in your conversation: {instance.content[:100]}..."
        else:
            title = f"New message from {instance.sender.username}"
            message_content = f"You have a new message: {instance.content[:100]}..."
        
        Notification.objects.create(
            user=target_user,
            message=instance,
            notification_type=notification_type,
            title=title,
            message_content=message_content
        )
        
        # Invalidate relevant caches
        cache_keys = [
            f"user_{target_user.id}_unread_notifications",
            f"user_{target_user.id}_conversations",
            f"thread_{instance.get_thread_root().id}_messages",
        ]
        for key in cache_keys:
            cache.delete(key)

@receiver(post_save, sender=Message)
def mark_thread_as_unread(sender, instance, created, **kwargs):
    """
    When a reply is added, mark the thread as having new activity
    """
    if created and instance.parent_message:
        # Update thread activity timestamp (you could add a last_activity field)
        root_message = instance.get_thread_root()
        # You could update a last_activity field here if you add one
        pass