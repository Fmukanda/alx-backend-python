# apps/core/middleware/logging.py
import logging
import time
from datetime import datetime
from django.http import JsonResponse
import json

logger = logging.getLogger(__name__)

class RequestResponseLoggingMiddleware:
    """
    Middleware to log incoming requests and outgoing responses.
    Logs request method, path, user, IP, response status, and processing time.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.setup_logging()

    def setup_logging(self):
        """Configure structured logging for requests and responses"""
        file_handler = logging.FileHandler('api_requests.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        request_logger = logging.getLogger('request_logger')
        request_logger.setLevel(logging.INFO)
        request_logger.addHandler(file_handler)
        request_logger.propagate = False

    def __call__(self, request):
        # Start timer
        start_time = time.time()
        
        # Log request details
        request_logger = logging.getLogger('request_logger')
        
        user_info = self._get_user_info(request)
        ip_address = self._get_client_ip(request)
        
        request_info = {
            'timestamp': datetime.now().isoformat(),
            'type': 'request',
            'method': request.method,
            'path': request.path,
            'user': user_info,
            'ip_address': ip_address,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'content_type': request.content_type,
        }
        
        request_logger.info(f"REQUEST: {json.dumps(request_info)}")
        
        # Process the request
        response = self.get_response(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log response details
        response_info = {
            'timestamp': datetime.now().isoformat(),
            'type': 'response',
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'processing_time': round(processing_time, 4),
            'user': user_info,
            'ip_address': ip_address,
        }
        
        request_logger.info(f"RESPONSE: {json.dumps(response_info)}")
        
        # Add processing time header
        response['X-Processing-Time'] = str(processing_time)
        
        return response

    def _get_user_info(self, request):
        """Extract user information from request"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return {
                'id': request.user.id,
                'username': request.user.username,
                'email': getattr(request.user, 'email', ''),
                'role': getattr(request.user, 'role', 'user')
            }
        return {'id': None, 'username': 'anonymous'}

    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PerformanceMonitoringMiddleware:
    """
    Middleware to monitor and log slow requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = 2.0  # seconds

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        processing_time = time.time() - start_time
        
        if processing_time > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.path} "
                f"took {processing_time:.2f}s (user: {getattr(request.user, 'username', 'anonymous')})"
            )
        
        return response