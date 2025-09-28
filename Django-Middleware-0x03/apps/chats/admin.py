from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Conversation, ConversationParticipant, Message, MessageRecipient

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_online', 'last_seen')
    list_filter = ('role', 'is_online', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('phone_number', 'role', 'profile_picture', 'is_online')
        }),
    )

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('conversation_id', 'is_group', 'group_name', 'created_at')
    list_filter = ('is_group', 'created_at')
    search_fields = ('group_name', 'participants__user__email')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'sender', 'conversation', 'message_type', 'sent_at', 'read')
    list_filter = ('message_type', 'read', 'sent_at')
    search_fields = ('message_body', 'sender__email')

admin.site.register(ConversationParticipant)
admin.site.register(MessageRecipient)


