# messaging/views.py (add this at the bottom)
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'messaging API',
        'timestamp': timezone.now().isoformat()
    })
