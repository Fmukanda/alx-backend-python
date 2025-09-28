# messaging/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

# Create a DefaultRouter instance - this automatically generates URLs for viewsets
router = routers.DefaultRouter()

# Register viewsets with the router
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ConversationParticipantViewSet, basename='participant')

# Create nested routers for conversations
conversations_router = routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', views.MessageViewSet, basename='conversation-messages')
conversations_router.register(r'participants', views.ConversationParticipantViewSet, basename='conversation-participants')

# Create nested routers for messages (if needed for replies, etc.)
messages_router = routers.NestedDefaultRouter(router, r'messages', lookup='message')
messages_router.register(r'replies', views.MessageViewSet, basename='message-replies')

# Custom URL patterns for additional endpoints that aren't covered by the router
custom_urlpatterns = [
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
    
    # Alternative search endpoints
    path('conversations/search/', views.ConversationViewSet.as_view({'get': 'search'}), name='conversation-search'),
    path('messages/search/', views.MessageViewSet.as_view({'get': 'search'}), name='message-search'),
    
    # Bulk actions
    path('messages/mark_conversation_read/', views.MessageViewSet.as_view({'post': 'mark_conversation_read'}), name='mark-conversation-read'),
    
    # User search endpoint
    path('users/search/', views.ConversationViewSet.as_view({'get': 'search_users'}), name='user-search'),
]

# Combine router URLs with custom URLs
urlpatterns = [
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
    path('', include(messages_router.urls)),
    path('', include(custom_urlpatterns)),
]

# Optional: Add JWT authentication endpoints if needed
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# 
# urlpatterns += [
#     path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
#     path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
# ]
