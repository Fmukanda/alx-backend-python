from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

"""routers.DefaultRouter()"""
router = DefaultRouter()  
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'participants', views.ConversationParticipantViewSet, basename='participant')

urlpatterns = [
    path('api/', include(router.urls)),
]

# Optional: Add these for more specific endpoints
urlpatterns += [
    path('api/conversations/<uuid:conversation_id>/messages/', 
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages'),
]

