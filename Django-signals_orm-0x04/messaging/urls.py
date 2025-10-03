from django.urls import path
from . import views

urlpatterns = [
    path('send_message/<int:receiver_id>/', views.send_message, name='send_message'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # New URLs for message editing and history
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('message/<int:message_id>/history/', views.message_history, name='message_history'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    
    # User account management
    path('account/settings/', views.account_settings, name='account_settings'),
    path('account/delete/', views.delete_account, name='delete_account'),
    path('api/account/delete/', views.delete_account_api, name='delete_account_api'),

    # Threaded conversations
    path('conversations/', views.conversations_list, name='conversations_list'),
    path('conversations/search/', views.search_conversations, name='search_conversations'),
    path('thread/<int:message_id>/', views.message_thread, name='message_thread'),
    path('thread/<int:message_id>/reply/', views.send_reply, name='send_reply'),
    path('api/thread/<int:message_id>/', views.get_thread_json, name='get_thread_json'),

    # Unread messages
    path('unread/', views.unread_messages, name='unread_messages'),
    path('message/<int:message_id>/mark-read/', views.mark_message_read, name='mark_message_read'),
    path('conversation/<int:message_id>/mark-read/', views.mark_conversation_read, name='mark_conversation_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/unread/count/', views.unread_messages_count_api, name='unread_messages_count_api'),
    path('api/unread/messages/', views.unread_messages_api, name='unread_messages_api')
]