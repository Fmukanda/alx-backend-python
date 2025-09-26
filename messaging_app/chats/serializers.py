from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Conversation, ConversationParticipant, Message, MessageRecipient


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = (
            'user_id', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'phone_number', 'role'
        )
        read_only_fields = ('user_id',)
    
    def validate_email(self, value):
        """Validate that email is unique and properly formatted"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate(self, data):
        """Validate that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data
    
    def create(self, validated_data):
        """Create a new user with encrypted password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user authentication"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(username=email.lower(), password=password)
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            data['user'] = user
            return data
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (read-only)"""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = (
            'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'role', 'profile_picture', 'is_online', 
            'last_seen', 'created_at'
        )
        read_only_fields = ('user_id', 'email', 'created_at')


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'phone_number', 
            'profile_picture', 'is_online'
        )
    
    def update(self, instance, validated_data):
        # Handle profile picture upload if needed
        return super().update(instance, validated_data)


class MinimalUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested relationships"""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ('user_id', 'email', 'first_name', 'last_name', 'full_name', 'profile_picture', 'is_online')
        read_only_fields = fields


class MessageRecipientSerializer(serializers.ModelSerializer):
    """Serializer for message recipients"""
    recipient = MinimalUserSerializer(read_only=True)
    
    class Meta:
        model = MessageRecipient
        fields = ('id', 'recipient', 'read', 'read_at', 'delivered', 'delivered_at')
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    sender = MinimalUserSerializer(read_only=True)
    recipients = MessageRecipientSerializer(many=True, read_only=True)
    replied_to = serializers.SlugRelatedField(
        slug_field='message_id', 
        queryset=Message.objects.all(), 
        required=False, 
        allow_null=True
    )
    replied_to_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'message_id', 'conversation', 'sender', 'message_body', 
            'message_type', 'attachment', 'attachment_name', 'replied_to',
            'replied_to_preview', 'sent_at', 'read', 'read_at', 'recipients'
        )
        read_only_fields = ('message_id', 'sender', 'sent_at', 'read_at', 'recipients')
    
    def get_replied_to_preview(self, obj):
        """Get preview of replied message"""
        if obj.replied_to:
            return obj.replied_to.preview
        return None
    
    def create(self, validated_data):
        """Create a new message"""
        # Set the sender from the request user
        validated_data['sender'] = self.context['request'].user
        message = Message.objects.create(**validated_data)
        
        # Create recipient entries for all conversation participants except sender
        conversation = validated_data['conversation']
        participants = conversation.participants.exclude(user=validated_data['sender'])
        
        for participant in participants:
            MessageRecipient.objects.create(
                message=message,
                recipient=participant.user,
                delivered=True  # Assuming immediate delivery for simplicity
            )
        
        return message


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer for conversation participants"""
    user = MinimalUserSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = ('id', 'user', 'joined_at', 'is_active', 'role')
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing conversations (with minimal data)"""
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = (
            'conversation_id', 'is_group', 'group_name', 'group_description',
            'participants', 'other_participants', 'last_message', 'unread_count',
            'created_at', 'updated_at'
        )
        read_only_fields = fields
    
    def get_last_message(self, obj):
        """Get the last message in the conversation"""
        last_message = obj.last_message
        if last_message:
            return {
                'message_id': last_message.message_id,
                'sender': MinimalUserSerializer(last_message.sender).data,
                'preview': last_message.preview,
                'message_type': last_message.message_type,
                'sent_at': last_message.sent_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.unread_count(request.user)
        return 0
    
    def get_other_participants(self, obj):
        """Get participants excluding the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participants = obj.participants.exclude(user=request.user)
            return ConversationParticipantSerializer(participants, many=True).data
        return ConversationParticipantSerializer(obj.participants, many=True).data


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for conversation details with messages"""
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    other_participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = (
            'conversation_id', 'is_group', 'group_name', 'group_description',
            'participants', 'other_participants', 'messages', 
            'created_at', 'updated_at'
        )
        read_only_fields = fields
    
    def get_messages(self, obj):
        """Get paginated messages for the conversation"""
        request = self.context.get('request')
        messages = obj.messages.all().order_by('-sent_at')[:50]  # Last 50 messages
        
        # Mark messages as read for the current user
        if request and request.user.is_authenticated:
            unread_messages = messages.exclude(sender=request.user).filter(read=False)
            for message in unread_messages:
                message.mark_as_read()
        
        return MessageSerializer(messages, many=True, context=self.context).data
    
    def get_other_participants(self, obj):
        """Get participants excluding the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participants = obj.participants.exclude(user=request.user)
            return ConversationParticipantSerializer(participants, many=True).data
        return ConversationParticipantSerializer(obj.participants, many=True).data


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversations"""
    participant_emails = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False
    )
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Conversation
        fields = (
            'conversation_id', 'is_group', 'group_name', 'group_description',
            'participant_emails', 'participant_ids', 'created_at'
        )
        read_only_fields = ('conversation_id', 'created_at')
    
    def validate(self, data):
        """Validate conversation creation data"""
        is_group = data.get('is_group', False)
        group_name = data.get('group_name')
        participant_emails = data.get('participant_emails', [])
        participant_ids = data.get('participant_ids', [])
        
        if is_group and not group_name:
            raise serializers.ValidationError({
                "group_name": "Group name is required for group conversations."
            })
        
        if not participant_emails and not participant_ids:
            raise serializers.ValidationError({
                "participants": "At least one participant is required."
            })
        
        return data
    
    def create(self, validated_data):
        """Create a new conversation with participants"""
        participant_emails = validated_data.pop('participant_emails', [])
        participant_ids = validated_data.pop('participant_ids', [])
        request = self.context.get('request')
        
        # Create conversation
        conversation = Conversation.objects.create(**validated_data)
        
        # Add current user as participant
        if request and request.user.is_authenticated:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=request.user,
                role='admin' if validated_data.get('is_group') else 'member'
            )
        
        # Add participants by email
        for email in participant_emails:
            try:
                user = User.objects.get(email=email.lower())
                ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=user
                )
            except User.DoesNotExist:
                # Handle case where user doesn't exist
                continue
        
        # Add participants by ID
        for user_id in participant_ids:
            try:
                user = User.objects.get(user_id=user_id)
                ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=user
                )
            except User.DoesNotExist:
                # Handle case where user doesn't exist
                continue
        
        return conversation


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = (
            'message_id', 'conversation', 'message_body', 'message_type',
            'attachment', 'attachment_name', 'replied_to', 'sent_at'
        )
        read_only_fields = ('message_id', 'sent_at')
    
    def validate_conversation(self, value):
        """Validate that user is a participant in the conversation"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not value.participants.filter(user=request.user).exists():
                raise serializers.ValidationError(
                    "You are not a participant in this conversation."
                )
        return value
    
    def create(self, validated_data):
        """Create a new message with the current user as sender"""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ConversationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating conversation details"""
    
    class Meta:
        model = Conversation
        fields = ('group_name', 'group_description')
    
    def update(self, instance, validated_data):
        """Update conversation details"""
        return super().update(instance, validated_data)


class UserSearchSerializer(serializers.ModelSerializer):
    """Serializer for user search results"""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ('user_id', 'email', 'first_name', 'last_name', 'full_name', 'profile_picture')
        read_only_fields = fields


class MessageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating messages (mainly for read status)"""
    
    class Meta:
        model = Message
        fields = ('read',)
    
    def update(self, instance, validated_data):
        """Update message read status"""
        read = validated_data.get('read', False)
        if read and not instance.read:
            instance.mark_as_read()
        return instance


class ConversationParticipantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating participant roles"""
    
    class Meta:
        model = ConversationParticipant
        fields = ('role', 'is_active')
    
    def validate_role(self, value):
        """Validate role assignment"""
        if value not in ['member', 'admin']:
            raise serializers.ValidationError("Invalid role. Must be 'member' or 'admin'.")
        return value


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for file attachments"""
    attachment = serializers.FileField()
    attachment_name = serializers.CharField(required=False)
    
    def validate_attachment(self, value):
        """Validate file size and type"""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must be less than 10MB.")
        
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                        'text/plain', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("File type not allowed.")
        
        return value

# For creating a conversation
"""serializer = ConversationCreateSerializer(data=request.data, context={'request': request})"""
# For listing conversations with last message preview
"""serializer = ConversationListSerializer(conversations, many=True, context={'request': request})"""
# For detailed conversation view with messages
"""serializer = ConversationDetailSerializer(conversation, context={'request': request})"""
