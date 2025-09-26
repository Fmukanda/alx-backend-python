# messaging/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
# routers.DefaultRouter()
router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ConversationParticipantViewSet, basename='participant')

# Custom URL patterns for additional endpoints
urlpatterns = [
    # Include all router-generated URLs
    path('', include(router.urls)),
    
    # Additional custom endpoints that aren't covered by the router
    path('conversations/<uuid:conversation_id>/messages/', 
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages-list'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
]

# Add this if you want to include user search directly under conversations
urlpatterns += [
    path('conversations/search/users/', 
         views.ConversationViewSet.as_view({'get': 'search_users'}), 
         name='conversation-search-users'),
]

