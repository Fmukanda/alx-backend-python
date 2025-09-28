# messaging/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .auth_views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    ChangePasswordView,
    refresh_token_view
)

# Create a DefaultRouter instance
router = routers.DefaultRouter()

# Register viewsets with the router
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ConversationParticipantViewSet, basename='participant')

# Create nested routers for conversations
conversations_router = routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', views.MessageViewSet, basename='conversation-messages')
conversations_router.register(r'participants', views.ConversationParticipantViewSet, basename='conversation-participants')

# Authentication URLs
auth_urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/refresh-custom/', refresh_token_view, name='token_refresh_custom'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]

# Custom URL patterns for additional endpoints
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

# Combine all URLs
urlpatterns = [
    # Authentication endpoints
    path('auth/', include(auth_urlpatterns)),
    
    # API endpoints
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
    path('', include(custom_urlpatterns)),
]
