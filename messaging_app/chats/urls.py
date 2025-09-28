# messaging/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a DefaultRouter instance - this automatically generates URLs for viewsets
# routers.DefaultRouter()
router = DefaultRouter()

# Register viewsets with the router
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ConversationParticipantViewSet, basename='participant')

# Custom URL patterns for additional endpoints that aren't covered by the router
custom_urlpatterns = [
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
    
    # Alternative endpoint for conversation messages (more RESTful)
    path('conversations/<uuid:conversation_id>/messages/', 
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages'),
]

# Combine router URLs with custom URLs
urlpatterns = [
    path('', include(router.urls)),
    path('', include(custom_urlpatterns)),
]

# Optional: Add JWT authentication endpoints if needed
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# 
# urlpatterns += [
#     path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
#     path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
# ]

