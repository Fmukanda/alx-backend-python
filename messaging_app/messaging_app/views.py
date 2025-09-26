# messaging/views.py (add this at the bottom)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

@api_view(['GET'])
@permission_classes([])  # No authentication required
def health_check(request):
    """
    Health check endpoint for API monitoring
    """
    return Response({
        'status': 'healthy',
        'service': 'Messaging API',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })
