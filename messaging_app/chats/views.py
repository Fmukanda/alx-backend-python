from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_group', 'conversation_type']
    
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
        queryset = Conversation.objects.filter(
            participants__user=user,
            participants__is_active=True
        ).distinct().order_by('-updated_at')
        
        # Additional filtering based on query parameters
        is_group = self.request.query_params.get('is_group')
        if is_group is not None:
            if is_group.lower() == 'true':
                queryset = queryset.filter(is_group=True)
            elif is_group.lower() == 'false':
                queryset = queryset.filter(is_group=False)
        
        conversation_type = self.request.query_params.get('conversation_type')
        if conversation_type:
            queryset = queryset.filter(conversation_type=conversation_type)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List conversations with optimized querying and filtering"""
        queryset = self.filter_queryset(self.get_queryset())
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
        
        # Filter participants by role if provided
        role = request.query_params.get('role')
        if role:
            participants = participants.filter(role=role)
            
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
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search conversations by name or participant names"""
        search_query = request.query_params.get('q', '')
        
        if not search_query:
            return Response(
                {"detail": "Query parameter 'q' is required for search."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get base queryset for current user
        user_conversations = self.get_queryset()
        
        # Search in conversation names (for groups) or participant names (for 1-on-1)
        conversations = user_conversations.filter(
            Q(name__icontains=search_query) |  # Group conversations with names
            Q(participants__user__first_name__icontains=search_query) |  # Participant first name
            Q(participants__user__last_name__icontains=search_query) |   # Participant last name
            Q(participants__user__email__icontains=search_query)         # Participant email
        ).distinct()
        
        # Apply additional filters if present
        conversations = self.filter_queryset(conversations)
        
        page = self.paginate_queryset(conversations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling messages
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['message_type', 'read', 'sender']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """Return messages from conversations where user is a participant"""
        user = self.request.user
        queryset = Message.objects.filter(
            conversation__participants__user=user,
            conversation__participants__is_active=True
        ).distinct().order_by('-sent_at')
        
        # Additional filtering based on query parameters
        message_type = self.request.query_params.get('message_type')
        if message_type:
            queryset = queryset.filter(message_type=message_type)
        
        read_status = self.request.query_params.get('read')
        if read_status is not None:
            if read_status.lower() == 'true':
                queryset = queryset.filter(read=True)
            elif read_status.lower() == 'false':
                queryset = queryset.filter(read=False)
        
        sender_id = self.request.query_params.get('sender')
        if sender_id:
            queryset = queryset.filter(sender__user_id=sender_id)
        
        return queryset
    
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
        
        messages = self.filter_queryset(self.get_queryset().filter(conversation=conversation))
        
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
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages by content within user's conversations"""
        search_query = request.query_params.get('q', '')
        conversation_id = request.query_params.get('conversation')
        
        if not search_query:
            return Response(
                {"detail": "Query parameter 'q' is required for search."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Base queryset - messages from user's conversations
        messages = self.get_queryset().filter(
            message_body__icontains=search_query
        )
        
        # Filter by specific conversation if provided
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                conversation_id=conversation_id,
                participants__user=request.user,
                participants__is_active=True
            )
            messages = messages.filter(conversation=conversation)
        
        # Apply additional filters
        messages = self.filter_queryset(messages)
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class ConversationParticipantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversation participants (admin only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationParticipantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'is_active']
    
    def get_queryset(self):
        """Return participants for conversations where user is admin"""
        user = self.request.user
        
        queryset = ConversationParticipant.objects.filter(
            conversation__participants__user=user,
            conversation__participants__role='admin',
            conversation__is_group=True
        ).distinct()
        
        # Additional filtering based on query parameters
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)
        
        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List participants with filtering"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
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
    
    @action(detail=False, methods=['get'])
    def conversation_participants(self, request):
        """Get all participants for a specific conversation where user is admin"""
        conversation_id = request.query_params.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {"detail": "conversation_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is admin in this conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__user=request.user,
            participants__role='admin',
            participants__is_active=True,
            is_group=True
        )
        
        participants = ConversationParticipant.objects.filter(
            conversation=conversation,
            is_active=True
        )
        
        # Apply filters
        participants = self.filter_queryset(participants)
        
        serializer = self.get_serializer(participants, many=True)
        return Response(serializer.data)
