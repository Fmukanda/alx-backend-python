from django.contrib import admin
from .models import Message, Notification, MessageHistory

class MessageHistoryInline(admin.TabularInline):
    model = MessageHistory
    extra = 0
    readonly_fields = ['edited_at', 'edited_by', 'old_content', 'new_content']
    can_delete = False

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'timestamp', 'edited', 'edit_count', 'is_read']
    list_filter = ['timestamp', 'edited', 'is_read']
    search_fields = ['content', 'sender__username', 'receiver__username']
    readonly_fields = ['edit_count', 'edited_at']
    inlines = [MessageHistoryInline]

@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ['message', 'edited_by', 'edited_at', 'edit_reason']
    list_filter = ['edited_at']
    search_fields = ['old_content', 'new_content', 'message__id']
    readonly_fields = ['edited_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'user__username', 'message_content']