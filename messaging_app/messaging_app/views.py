from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint that doesn't require authentication"""
    return Response({
        'status': 'healthy',
        'message': 'Messaging API is running',
        'timestamp': timezone.now().isoformat()
    })
