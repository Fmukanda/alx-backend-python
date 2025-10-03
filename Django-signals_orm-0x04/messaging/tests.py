from django.test import TestCase
from django.contrib.auth.models import User
from .models import Message, Notification

class SignalTestCase(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user('sender', 'sender@test.com', 'password')
        self.receiver = User.objects.create_user('receiver', 'receiver@test.com', 'password')
    
    def test_message_creates_notification(self):
        """Test that creating a message automatically creates a notification"""
        # Check initial state
        self.assertEqual(Notification.objects.count(), 0)
        
        # Create a message
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test message content"
        )
        
        # Verify notification was created
        self.assertEqual(Notification.objects.count(), 1)
        
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.receiver)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.sender.username, notification.title)
