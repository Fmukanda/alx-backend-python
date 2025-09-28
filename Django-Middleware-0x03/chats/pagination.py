# chats/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class MessagePagination(PageNumberPagination):
    """
    Custom pagination for messages - 20 messages per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'results': data
        })

class ConversationPagination(PageNumberPagination):
    """
    Custom pagination for conversations
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class UserPagination(PageNumberPagination):
    """
    Custom pagination for user search results
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50
