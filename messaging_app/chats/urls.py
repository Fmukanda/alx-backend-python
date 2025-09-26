from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router with custom settings
router = DefaultRouter(trailing_slash=False)  # Remove trailing slashes

# Register viewsets - the router will automatically generate these URLs:
# - /api/conversations/
# - /api/conversations/{pk}/
# - /api/messages/
# - /api/messages/{pk}/
# - /api/participants/
# - /api/participants/{pk}/
router.register(r'conversations', views.ConversationViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'participants', views.ConversationParticipantViewSet)

# URL patterns
urlpatterns = [
    # Include all router-generated URLs
    path('', include(router.urls)),
]

# Add health check endpoint
urlpatterns += [
    path('health', views.health_check, name='health-check'),
]
