import django_filters
from .models import Message, Conversation
from django.contrib.auth import get_user_model
from django import forms
import datetime

User = get_user_model()

class MessageFilter(django_filters.FilterSet):
    """
    Filter class for messages with advanced filtering options
    """
    conversation = django_filters.ModelChoiceFilter(
        field_name='conversation',
        queryset=Conversation.objects.all(),
        label='Conversation'
    )
    
    sender = django_filters.ModelChoiceFilter(
        field_name='sender',
        queryset=User.objects.all(),
        label='Sender'
    )
    
    message_type = django_filters.ChoiceFilter(
        choices=Message.MESSAGE_TYPE_CHOICES,
        label='Message Type'
    )
    
    read = django_filters.BooleanFilter(
        label='Read Status'
    )
    
    # Date range filtering
    start_date = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='gte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='From Date'
    )
    
    end_date = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='lte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='To Date'
    )
    
    # Today's messages
    today = django_filters.BooleanFilter(
        method='filter_today',
        label="Today's Messages"
    )
    
    # Search in message content
    search = django_filters.CharFilter(
        method='filter_search',
        label='Search in Messages'
    )
    
    # Unread messages only
    unread_only = django_filters.BooleanFilter(
        method='filter_unread',
        label='Unread Messages Only'
    )
    
    class Meta:
        model = Message
        fields = [
            'conversation', 
            'sender', 
            'message_type', 
            'read',
            'start_date',
            'end_date'
        ]
    
    def filter_today(self, queryset, name, value):
        """Filter messages from today"""
        if value:
            today = datetime.date.today()
            return queryset.filter(sent_at__date=today)
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search in message body"""
        if value:
            return queryset.filter(message_body__icontains=value)
        return queryset
    
    def filter_unread(self, queryset, name, value):
        """Filter unread messages for current user"""
        if value and hasattr(self.request, 'user'):
            return queryset.filter(read=False).exclude(sender=self.request.user)
        return queryset

class ConversationFilter(django_filters.FilterSet):
    """
    Filter class for conversations
    """
    is_group = django_filters.BooleanFilter(
        label='Group Conversation'
    )
    
    participant = django_filters.ModelChoiceFilter(
        field_name='participants__user',
        queryset=User.objects.all(),
        label='Participant'
    )
    
    participant_email = django_filters.CharFilter(
        method='filter_by_participant_email',
        label='Participant Email'
    )
    
    has_unread = django_filters.BooleanFilter(
        method='filter_has_unread',
        label='Has Unread Messages'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    search = django_filters.CharFilter(
        method='filter_search',
        label='Search in Conversations'
    )
    
    class Meta:
        model = Conversation
        fields = ['is_group']
    
    def filter_by_participant_email(self, queryset, name, value):
        """Filter conversations by participant email"""
        if value:
            return queryset.filter(participants__user__email__iexact=value)
        return queryset
    
    def filter_has_unread(self, queryset, name, value):
        """Filter conversations that have unread messages for current user"""
        if value and hasattr(self.request, 'user'):
            return queryset.filter(
                messages__read=False,
                messages__recipients__recipient=self.request.user
            ).distinct()
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search in conversation names or participant names"""
        if value:
            return queryset.filter(
                django_filters.Q(group_name__icontains=value) |
                django_filters.Q(participants__user__first_name__icontains=value) |
                django_filters.Q(participants__user__last_name__icontains=value) |
                django_filters.Q(participants__user__email__icontains=value)
            ).distinct()
        return queryset

class UserFilter(django_filters.FilterSet):
    """
    Filter class for user search
    """
    role = django_filters.ChoiceFilter(
        choices=User.ROLE_CHOICES,
        label='User Role'
    )
    
    is_online = django_filters.BooleanFilter(
        label='Online Status'
    )
    
    search = django_filters.CharFilter(
        method='filter_search',
        label='Search Users'
    )
    
    class Meta:
        model = User
        fields = ['role', 'is_online']
    
    def filter_search(self, queryset, name, value):
        """Search users by name or email"""
        if value:
            return queryset.filter(
                django_filters.Q(first_name__icontains=value) |
                django_filters.Q(last_name__icontains=value) |
                django_filters.Q(email__icontains=value)
            )
        return queryset
