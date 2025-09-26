import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Custom user manager for handling user creation"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model extending AbstractUser"""
    
    class Role(models.TextChoices):
        GUEST = 'guest', _('Guest')
        HOST = 'host', _('Host')
        ADMIN = 'admin', _('Admin')
    
    # Override default username field to use email
    username = None
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    
    # Custom fields
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=10, 
        choices=Role.choices, 
        default=Role.GUEST,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional profile fields that might be useful for a messaging app
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_online']),
        ]
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"
    
    @property
    def full_name(self):
        return self.get_full_name()
    
    def save(self, *args, **kwargs):
        # Ensure email is lowercase
        self.email = self.email.lower()
        super().save(*args, **kwargs)


class Conversation(models.Model):
    """Model representing a conversation between multiple users"""
    
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=255, blank=True, null=True)
    group_description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'conversation'
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_group']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.is_group:
            return f"Group: {self.group_name or f'Conversation {self.conversation_id}'}"
        participants = self.participants.all()[:3]  # Get first 3 participants for display
        participant_names = [str(participant.user) for participant in participants]
        return f"Conversation between {', '.join(participant_names)}"
    
    @property
    def last_message(self):
        """Get the last message in the conversation"""
        return self.messages.order_by('-sent_at').first()
    
    @property
    def unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.exclude(sender=user).filter(read=False).count()


class ConversationParticipant(models.Model):
    """Through model for tracking users in conversations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='participants'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='conversations'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # For group conversations
    role = models.CharField(
        max_length=20, 
        choices=[('member', 'Member'), ('admin', 'Admin')], 
        default='member'
    )
    
    class Meta:
        db_table = 'conversation_participant'
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['conversation', 'user']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.conversation}"


class Message(models.Model):
    """Model representing a message in a conversation"""
    
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Message status and metadata
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # For message types and attachments
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('image', 'Image'),
            ('file', 'File'),
            ('system', 'System Message'),
        ],
        default='text'
    )
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, null=True)
    
    # For replied messages
    replied_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='replies'
    )
    
    class Meta:
        db_table = 'message'
        indexes = [
            models.Index(fields=['message_id']),
            models.Index(fields=['conversation', 'sent_at']),
            models.Index(fields=['sender', 'sent_at']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['read']),
        ]
        ordering = ['sent_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} at {self.sent_at}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def preview(self):
        """Get a shortened preview of the message"""
        if len(self.message_body) > 50:
            return self.message_body[:50] + '...'
        return self.message_body


class MessageRecipient(models.Model):
    """Through model for tracking message delivery status to participants"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='recipients')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'message_recipient'
        unique_together = ['message', 'recipient']
        indexes = [
            models.Index(fields=['recipient', 'read']),
            models.Index(fields=['message', 'recipient']),
        ]
    
    def __str__(self):
        return f"Message {self.message.message_id} for {self.recipient.email}"


