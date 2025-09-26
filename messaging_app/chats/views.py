from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from .models import Conversation, Message, ConversationParticipant, User
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer, 
    ConversationCreateSerializer, ConversationUpdateSerializer,
    MessageSerializer, MessageCreateSerializer,
    ConversationParticipantSerializer, ConversationParticipantUpdateSerializer,
    UserSearchSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling conversations
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Conversation.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ConversationUpdateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer
    
    def get_queryset(self):
        """Return conversations where current user is a participant"""
        user = self.request.user
        return Conversation.objects.filter(
            participants__user=user,
            participants__is_active=True
        ).distinct().order_by('-updated_at')
    
    def list(self, request, *args, **kwargs):
        """List conversations with optimized querying"""
        queryset = self.get_queryset()
        queryset = queryset.prefetch_related(
            'participants__user',
            'messages__sender'
        )
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve conversation details with messages"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        conversation = serializer.save()
        
        # Return conversation details
        detail_serializer = ConversationDetailSerializer(
            conversation, 
            context={'request': request}
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update conversation details (mainly for groups)"""
        instance = self.get_object()
        
        # Check if user is admin in the conversation
        participant = get_object_or_404(
            ConversationParticipant,
            conversation=instance,
            user=request.user,
            is_active=True
        )
        
        if instance.is_group and participant.role != 'admin':
            return Response(
                {"detail": "Only admins can update group conversations."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_participants(self, request, pk=None):
        """Add participants to a conversation"""
        conversation = self.get_object()
        
        # Check if user is admin or conversation is not group
        participant = get_object_or_404(
            ConversationParticipant,
            conversation=conversation,
            user=request.user,
            is_active=True
        )
        
        if conversation.is_group and participant.role != 'admin':
            return Response(
                {"detail": "Only admins can add participants to group conversations."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        participant_emails = request.data.get('participant_emails', [])
        participant_ids = request.data.get('participant_ids', [])
        
        added_users = []
        for email in participant_emails:
            try:
                user = User.objects.get(email=email.lower())
                participant, created = ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=user,
                    defaults={'is_active': True}
                )
                if created:
                    added_users.append(user)
            except User.DoesNotExist:
                continue
        
        for user_id in participant_ids:
            try:
                user = User.objects.get(user_id=user_id)
                participant, created = ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=user,
                    defaults={'is_active': True}
                )
                if created:
                    added_users.append(user)
            except User.DoesNotExist:
                continue
        
        serializer = UserSearchSerializer(added_users, many=True)
        return Response({
            "added_participants": serializer.data,
            "message": f"Added {len(added_users)} participants to the conversation."
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a conversation"""
        conversation = self.get_object()
        
        participant = get_object_or_404(
            ConversationParticipant,
            conversation=conversation,
            user=request.user,
            is_active=True
        )
        
        # For 1-on-1 conversations, deactivate the participant
        # For group conversations, remove the participant
        if not conversation.is_group:
            participant.is_active = False
            participant.save()
        else:
            participant.delete()
        
        return Response({"detail": "You have left the conversation."})
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get conversation participants"""
        conversation = self.get_object()
        participants = conversation.participants.filter(is_active=True)
        serializer = ConversationParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_users(self, request):
        """Search users to add to conversations"""
        query = request.query_params.get('q', '')
        
        if not query or len(query) < 2:
            return Response(
                {"detail": "Query parameter 'q' with at least 2 characters is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Exclude current user and search by name or email
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(user_id=request.user.user_id)
        
        serializer = UserSearchSerializer(users, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling messages
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """Return messages from conversations where user is a participant"""
        user = self.request.user
        return Message.objects.filter(
            conversation__participants__user=user,
            conversation__participants__is_active=True
        ).distinct().order_by('-sent_at')
    
    def list(self, request, *args, **kwargs):
        """List messages with conversation filtering"""
        conversation_id = request.query_params.get('conversation')
        
        if not conversation_id:
            return Response(
                {"detail": "Conversation ID is required as query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user has access to this conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__user=request.user,
            participants__is_active=True
        )
        
        messages = self.get_queryset().filter(conversation=conversation)
        
        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new message"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        message = serializer.save()
        
        # Update conversation's updated_at timestamp
        message.conversation.save()
        
        # Return the created message with full details
        detail_serializer = MessageSerializer(message, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific message"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        # Check if user is a recipient of this message
        if message.sender != request.user:
            message.mark_as_read()
            
            # Also update the MessageRecipient record
            try:
                recipient = MessageRecipient.objects.get(
                    message=message,
                    recipient=request.user
                )
                recipient.read = True
                recipient.save()
            except MessageRecipient.DoesNotExist:
                pass
        
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_conversation_read(self, request):
        """Mark all messages in a conversation as read"""
        conversation_id = request.data.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {"detail": "conversation_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__user=request.user,
            participants__is_active=True
        )
        
        # Mark messages as read
        unread_messages = Message.objects.filter(
            conversation=conversation
        ).exclude(sender=request.user).filter(read=False)
        
        for message in unread_messages:
            message.mark_as_read()
        
        return Response({
            "detail": f"Marked {unread_messages.count()} messages as read.",
            "conversation_id": conversation_id
        })
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Create a reply to a message"""
        original_message = self.get_object()
        
        reply_data = {
            'conversation': original_message.conversation.conversation_id,
            'message_body': request.data.get('message_body'),
            'replied_to': original_message.message_id,
            'message_type': request.data.get('message_type', 'text')
        }
        
        serializer = MessageCreateSerializer(
            data=reply_data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        reply_message = serializer.save()
        detail_serializer = MessageSerializer(reply_message, context={'request': request})
        
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class ConversationParticipantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversation participants (admin only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationParticipantSerializer
    
    def get_queryset(self):
        """Return participants for conversations where user is admin"""
        user = self.request.user
        return ConversationParticipant.objects.filter(
            conversation__participants__user=user,
            conversation__participants__role='admin',
            conversation__is_group=True
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def update_role(self, request, pk=None):
        """Update participant role (admin only)"""
        participant = self.get_object()
        
        # Check if requester is admin in the conversation
        requester_participant = get_object_or_404(
            ConversationParticipant,
            conversation=participant.conversation,
            user=request.user,
            role='admin',
            is_active=True
        )
        
        serializer = ConversationParticipantUpdateSerializer(
            participant, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
