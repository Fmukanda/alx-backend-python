# chats/filters.py
import django_filters
from .models import Message, Conversation
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageFilter(django_filters.FilterSet):
    conversation = django_filters.ModelChoiceFilter(
        field_name='conversation',
        queryset=Conversation.objects.all()
    )
    sender = django_filters.ModelChoiceFilter(
        field_name='sender',
        queryset=User.objects.all()
    )
    start_date = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='gte'
    )
    end_date = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='lte'
    )
    message_type = django_filters.ChoiceFilter(
        choices=Message.MESSAGE_TYPE_CHOICES
    )
    read = django_filters.BooleanFilter()
    
    class Meta:
        model = Message
        fields = ['conversation', 'sender', 'message_type', 'read']

class ConversationFilter(django_filters.FilterSet):
    is_group = django_filters.BooleanFilter()
    participant = django_filters.ModelChoiceFilter(
        field_name='participants__user',
        queryset=User.objects.all()
    )
    
    class Meta:
        model = Conversation
        fields = ['is_group', 'participant']
