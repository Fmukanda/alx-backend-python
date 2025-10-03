from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth.models import User
from .forms import UserDeleteForm
import logging
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from .models import Message, Notification, User
from .forms import MessageForm, ReplyForm
import json

logger = logging.getLogger(__name__)

@login_required
def delete_account(request):
    """
    View for users to delete their own account
    """
    if request.method == 'POST':
        form = UserDeleteForm(request.POST, user=request.user)
        
        if form.is_valid():
            # Verify password
            if not request.user.check_password(form.cleaned_data['password']):
                form.add_error('password', 'Invalid password')
                return render(request, 'delete_account.html', {'form': form})
            
            # Confirm deletion
            if form.cleaned_data['confirmation'] != 'DELETE MY ACCOUNT':
                form.add_error('confirmation', 'Please type the confirmation phrase exactly')
                return render(request, 'delete_account.html', {'form': form})
            
            # Store user info for logging before deletion
            user_id = request.user.id
            username = request.user.username
            email = request.user.email
            
            try:
                with transaction.atomic():
                    # Delete the user (this will trigger CASCADE deletions and our signals)
                    request.user.delete()
                    
                    # Logout the user
                    logout(request)
                    
                    logger.info(f"User account deleted: {username} (ID: {user_id}, Email: {email})")
                    
                    messages.success(
                        request, 
                        'Your account has been permanently deleted. '
                        'All your data has been removed from our systems.'
                    )
                    
                    return redirect('home')
                    
            except Exception as e:
                logger.error(f"Error deleting user account {username}: {str(e)}")
                messages.error(
                    request, 
                    'An error occurred while deleting your account. Please try again or contact support.'
                )
                return render(request, 'delete_account.html', {'form': form})
    
    else:
        form = UserDeleteForm()
    
    # Get user statistics for the confirmation page
    user_stats = {
        'sent_messages': request.user.sent_messages.count(),
        'received_messages': request.user.received_messages.count(),
        'notifications': request.user.notifications.count(),
        'edits_made': request.user.message_edits.count(),
    }
    
    context = {
        'form': form,
        'user_stats': user_stats,
    }
    
    return render(request, 'delete_account.html', context)

@require_POST
@login_required
def delete_account_api(request):
    """
    API endpoint for account deletion (for AJAX requests)
    """
    form = UserDeleteForm(request.POST, user=request.user)
    
    if form.is_valid():
        # Verify password
        if not request.user.check_password(form.cleaned_data['password']):
            return JsonResponse({
                'status': 'error',
                'errors': {'password': ['Invalid password']}
            }, status=400)
        
        # Confirm deletion phrase
        if form.cleaned_data['confirmation'] != 'DELETE MY ACCOUNT':
            return JsonResponse({
                'status': 'error',
                'errors': {'confirmation': ['Please type the confirmation phrase exactly']}
            }, status=400)
        
        try:
            with transaction.atomic():
                user_id = request.user.id
                username = request.user.username
                
                request.user.delete()
                logout(request)
                
                logger.info(f"User account deleted via API: {username} (ID: {user_id})")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Your account has been permanently deleted.',
                    'redirect_url': '/'
                })
                
        except Exception as e:
            logger.error(f"Error in API account deletion for {username}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while deleting your account.'
            }, status=500)
    
    else:
        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        }, status=400)

@login_required
def account_settings(request):
    """
    Account settings page with deletion option
    """
    user_stats = {
        'sent_messages': request.user.sent_messages.count(),
        'received_messages': request.user.received_messages.count(),
        'notifications': request.user.notifications.count(),
        'edits_made': request.user.message_edits.count(),
        'account_created': request.user.date_joined,
    }
    
    context = {
        'user_stats': user_stats,
    }
    
    return render(request, 'account_settings.html', context)

@login_required
def conversations_list(request):
    """
    Display all conversations (top-level messages) for the user
    """
    cache_key = f"user_{request.user.id}_conversations"
    conversations = cache.get(cache_key)
    
    if not conversations:
        conversations = Message.objects.get_conversations(request.user)
        
        # Annotate with unread counts and reply counts
        for conv in conversations:
            conv.unread_count = conv.replies.filter(is_read=False, receiver=request.user).count()
            if not conv.is_read and conv.receiver == request.user:
                conv.unread_count += 1
            conv.reply_count = conv.replies.count()
        
        cache.set(cache_key, conversations, 300)  # Cache for 5 minutes
    
    # Pagination
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'conversations': page_obj.object_list,
    }
    return render(request, 'conversations_list.html', context)

@login_required
def message_thread(request, message_id):
    """
    Display a message thread with all replies
    """
    cache_key = f"thread_{message_id}_messages"
    messages = cache.get(cache_key)
    
    if not messages:
        # Get the entire thread efficiently
        messages = Message.objects.get_message_thread(message_id, request.user)
        cache.set(cache_key, messages, 300)  # Cache for 5 minutes
    
    root_message = get_object_or_404(Message, id=message_id)
    
    # Build threaded structure
    def build_thread(messages_qs, parent=None, depth=0):
        thread = []
        for msg in messages_qs:
            if msg.parent_message == parent:
                thread.append({
                    'message': msg,
                    'depth': depth,
                    'replies': build_thread(messages_qs, msg, depth + 1)
                })
        return thread
    
    thread_structure = build_thread(messages)
    
    # Mark messages as read when viewing thread
    if request.user == root_message.receiver:
        unread_messages = messages.filter(is_read=False, receiver=request.user)
        unread_messages.update(is_read=True)
        
        # Invalidate cache
        cache.delete(f"user_{request.user.id}_unread_notifications")
        cache.delete(f"user_{request.user.id}_conversations")
    
    context = {
        'root_message': root_message,
        'thread_structure': thread_structure,
        'reply_form': ReplyForm(),
    }
    return render(request, 'message_thread.html', context)

@login_required
@require_POST
def send_reply(request, message_id):
    """
    Handle reply to a message
    """
    parent_message = get_object_or_404(
        Message, 
        id=message_id,
        Q(sender=request.user) | Q(receiver=request.user)
    )
    
    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.sender = request.user
        reply.receiver = parent_message.sender if request.user != parent_message.sender else parent_message.receiver
        reply.parent_message = parent_message
        reply.save()
        
        # Invalidate caches
        cache_keys = [
            f"user_{reply.receiver.id}_unread_notifications",
            f"user_{reply.receiver.id}_conversations",
            f"thread_{parent_message.get_thread_root().id}_messages",
        ]
        for key in cache_keys:
            cache.delete(key)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message_id': reply.id,
                'content': reply.content,
                'sender': reply.sender.username,
                'timestamp': reply.timestamp.isoformat(),
            })
        
        return redirect('message_thread', message_id=parent_message.get_thread_root().id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        }, status=400)
    
    return redirect('message_thread', message_id=message_id)

@login_required
def get_thread_json(request, message_id):
    """
    API endpoint to get thread data as JSON (for dynamic loading)
    """
    messages = Message.objects.get_message_thread(message_id, request.user)
    
    def build_json_thread(messages_qs, parent=None, depth=0):
        thread = []
        for msg in messages_qs:
            if msg.parent_message == parent:
                thread.append({
                    'id': msg.id,
                    'sender': msg.sender.username,
                    'receiver': msg.receiver.username,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_read': msg.is_read,
                    'edited': msg.edited,
                    'depth': depth,
                    'replies': build_json_thread(messages_qs, msg, depth + 1)
                })
        return thread
    
    thread_data = build_json_thread(messages)
    
    return JsonResponse({
        'thread': thread_data,
        'root_message_id': message_id
    })

@login_required
def search_conversations(request):
    """
    Search through conversations
    """
    query = request.GET.get('q', '')
    if query:
        # Search in messages where user is participant
        conversations = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
            Q(content__icontains=query) | 
            Q(sender__username__icontains=query) |
            Q(receiver__username__icontains=query)
        ).filter(parent_message__isnull=True).select_related('sender', 'receiver').distinct()
    else:
        conversations = Message.objects.get_conversations(request.user)
    
    context = {
        'conversations': conversations,
        'query': query,
    }
    return render(request, 'search_conversations.html', context)

    @login_required
def unread_messages(request):
    """
    Display only unread messages for the current user
    """
    cache_key = f"user_{request.user.id}_unread_messages"
    unread_messages = cache.get(cache_key)
    
    if not unread_messages:
        # Use the custom manager with optimized query
        unread_messages = Message.unread_objects.for_user(request.user)
        cache.set(cache_key, unread_messages, 300)  # Cache for 5 minutes
    
    # Group unread messages by conversation
    messages_by_conversation = {}
    for message in unread_messages:
        root_message = message.get_thread_root()
        if root_message.id not in messages_by_conversation:
            messages_by_conversation[root_message.id] = {
                'root_message': root_message,
                'unread_messages': []
            }
        messages_by_conversation[root_message.id]['unread_messages'].append(message)
    
    # Get unread count using the custom manager
    unread_count = Message.unread_objects.unread_count_for_user(request.user)
    
    # Pagination
    paginator = Paginator(list(messages_by_conversation.values()), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'unread_count': unread_count,
        'messages_by_conversation': messages_by_conversation,
    }
    return render(request, 'unread_messages.html', context)

@login_required
@require_POST
def mark_message_read(request, message_id):
    """
    Mark a specific message as read
    """
    message = get_object_or_404(
        Message, 
        id=message_id,
        receiver=request.user
    )
    
    message.mark_as_read()
    
    # Invalidate relevant caches
    cache.delete(f"user_{request.user.id}_unread_messages")
    cache.delete(f"user_{request.user.id}_unread_notifications")
    cache.delete(f"user_{request.user.id}_conversations")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': 'Message marked as read'
        })
    
    return redirect('unread_messages')

@login_required
@require_POST
def mark_conversation_read(request, message_id):
    """
    Mark all messages in a conversation as read
    """
    root_message = get_object_or_404(
        Message, 
        id=message_id,
        Q(sender=request.user) | Q(receiver=request.user)
    )
    
    # Get all messages in the thread that are unread and belong to the user
    thread_messages = Message.objects.get_message_thread(message_id, request.user)
    unread_messages = thread_messages.filter(
        receiver=request.user,
        is_read=False
    )
    
    # Use the custom manager to mark as read
    updated_count = Message.unread_objects.mark_as_read(
        request.user, 
        unread_messages.values_list('id', flat=True)
    )
    
    # Invalidate caches
    cache.delete(f"user_{request.user.id}_unread_messages")
    cache.delete(f"user_{request.user.id}_unread_notifications")
    cache.delete(f"user_{request.user.id}_conversations")
    cache.delete(f"thread_{message_id}_messages")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f'Marked {updated_count} messages as read'
        })
    
    messages.success(request, f'Marked {updated_count} messages as read')
    return redirect('unread_messages')

@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all unread messages as read for the current user
    """
    # Use the custom manager to mark all as read
    updated_count = Message.unread_objects.mark_as_read(request.user)
    
    # Invalidate all relevant caches
    cache_keys = [
        f"user_{request.user.id}_unread_messages",
        f"user_{request.user.id}_unread_notifications",
        f"user_{request.user.id}_conversations",
    ]
    for key in cache_keys:
        cache.delete(key)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f'Marked all {updated_count} messages as read'
        })
    
    messages.success(request, f'Marked all {updated_count} messages as read')
    return redirect('unread_messages')

@login_required
def unread_messages_count_api(request):
    """
    API endpoint to get unread message count
    """
    cache_key = f"user_{request.user.id}_unread_count"
    unread_count = cache.get(cache_key)
    
    if unread_count is None:
        unread_count = Message.unread_objects.unread_count_for_user(request.user)
        cache.set(cache_key, unread_count, 60)  # Cache for 1 minute
    
    return JsonResponse({
        'unread_count': unread_count,
        'user_id': request.user.id
    })

@login_required
def unread_messages_api(request):
    """
    API endpoint to get unread messages data
    """
    unread_messages = Message.unread_objects.for_user(request.user).values(
        'id',
        'content',
        'timestamp',
        'sender__username',
        'parent_message_id',
        'thread_depth'
    )[:50]  # Limit to 50 messages
    
    return JsonResponse({
        'unread_messages': list(unread_messages),
        'total_count': len(unread_messages)
    })