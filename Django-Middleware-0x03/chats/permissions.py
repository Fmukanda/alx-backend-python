# chats/permissions.py
from rest_framework import permissions

class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    Allow only authenticated users to access the API
    Allow only participants in a conversation to send, view, update and delete messages
    """
    
    def has_permission(self, request, view):
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False
        
        # For list/create actions, check in has_object_permission or allow
        if view.action in ['list', 'create']:
            return True
            
        # For detail actions, check object permission
        if view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
            
        return True

    def has_object_permission(self, request, view, obj):
        """
        Check if the user is a participant of the conversation
        """
        # Handle Conversation objects
        if hasattr(obj, 'participants'):
            return obj.participants.filter(user=request.user, is_active=True).exists()
        
        # Handle Message objects - check if user is participant in message's conversation
        elif hasattr(obj, 'conversation'):
            return obj.conversation.participants.filter(
                user=request.user, 
                is_active=True
            ).exists()
        
        # Handle ConversationParticipant objects
        elif hasattr(obj, 'conversation') and hasattr(obj, 'user'):
            # Users can access their own participant records
            if obj.user == request.user:
                return True
            # Check if user is participant in the conversation
            return obj.conversation.participants.filter(
                user=request.user, 
                is_active=True
            ).exists()
        
        return False

class IsMessageSender(permissions.BasePermission):
    """
    Permission to only allow message sender to update/delete their own messages
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Only allow message sender to update/delete
        return obj.sender == request.user

class IsConversationAdmin(permissions.BasePermission):
    """
    Permission to only allow conversation admins to perform admin actions
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Check if user is admin in this conversation
        participant = obj.participants.filter(
            user=request.user, 
            is_active=True
        ).first()
        
        return participant and participant.role == 'admin'
