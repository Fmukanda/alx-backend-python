from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Count, Case, When, IntegerField
from django.urls import reverse

class MessageManager(models.Manager):
    def get_conversations(self, user):
        """
        Get all conversations for a user (top-level messages and their threads)
        """
        return self.filter(
            Q(sender=user) | Q(receiver=user)
        ).filter(
            parent_message__isnull=True  # Only top-level messages
        ).select_related('sender', 'receiver').prefetch_related(
            'replies__sender', 
            'replies__receiver'
        ).order_by('-timestamp')
    
    def get_message_thread(self, message_id, user):
        """
        Get a specific message and all its replies in a single query
        """
        return self.filter(
            Q(id=message_id) | Q(parent_message_id=message_id),
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver', 'parent_message').order_by('timestamp')
    
    def get_unread_counts(self, user):
        """
        Get unread message counts for user's conversations
        """
        return self.filter(
            receiver=user,
            is_read=False
        ).values('parent_message_id').annotate(
            unread_count=Count('id')
        )

class Message(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    # Edit tracking fields
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    edit_count = models.PositiveIntegerField(default=0)
    
    # Threading fields
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
        help_text="If this is a reply, link to the parent message"
    )
    thread_depth = models.PositiveIntegerField(default=0, help_text="Depth in the reply thread")
    
    objects = MessageManager()
    
    class Meta:
        ordering = ['thread_depth', 'timestamp']
        indexes = [
            models.Index(fields=['parent_message', 'timestamp']),
            models.Index(fields=['sender', 'receiver', 'timestamp']),
            models.Index(fields=['thread_depth', 'timestamp']),
        ]
    
    def __str__(self):
        if self.parent_message:
            return f"Reply from {self.sender} in thread #{self.parent_message.id}"
        return f"Message from {self.sender} to {self.receiver}"
    
    def save(self, *args, **kwargs):
        # If this is a reply, set thread depth
        if self.parent_message:
            self.thread_depth = self.parent_message.thread_depth + 1
        else:
            self.thread_depth = 0
            
        # Edit tracking
        if self.pk:
            original = Message.objects.get(pk=self.pk)
            if original.content != self.content:
                self.edited = True
                self.edited_at = timezone.now()
                self.edit_count += 1
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('message_thread', kwargs={'message_id': self.id})
    
    def get_thread_root(self):
        """
        Get the root message of this thread
        """
        if self.parent_message:
            return self.parent_message.get_thread_root()
        return self
    
    def get_reply_count(self):
        """
        Get total number of replies in this thread
        """
        return self.replies.count()
    
    def get_all_replies(self, depth=0, max_depth=10):
        """
        Recursively get all replies with proper indentation
        """
        if depth > max_depth:
            return []
        
        replies = []
        for reply in self.replies.select_related('sender', 'receiver').all():
            replies.append({
                'message': reply,
                'depth': depth,
                'replies': reply.get_all_replies(depth + 1, max_depth)
            })
        return replies

class MessageHistory(models.Model):
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='history'
    )
    old_content = models.TextField()
    new_content = models.TextField()
    edited_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='message_edits'
    )
    edited_at = models.DateTimeField(default=timezone.now)
    edit_reason = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-edited_at']
        verbose_name_plural = 'Message histories'

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'New Message'),
        ('system', 'System Notification'),
        ('edit', 'Message Edited'),
        ('reply', 'New Reply'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES, 
        default='message'
    )
    title = models.CharField(max_length=255)
    message_content = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']