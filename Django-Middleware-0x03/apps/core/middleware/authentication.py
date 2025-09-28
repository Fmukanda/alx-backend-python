# apps/core/middleware/authentication.py
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RoleBasedAccessMiddleware:
    """
    Middleware to restrict access based on user roles.
    Provides role-based authorization for different endpoints.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.role_config = getattr(settings, 'ROLE_ACCESS_CONFIG', {})
        
        # Default role configuration
        self.default_config = {
            'admin': {
                'allowed_paths': ['*'],
                'allowed_methods': ['*'],
            },
            'moderator': {
                'allowed_paths': ['/api/', '/admin/core/', '/admin/chats/'],
                'allowed_methods': ['GET', 'POST', 'PUT', 'PATCH'],
                'denied_methods': ['DELETE']
            },
            'user': {
                'allowed_paths': ['/api/chats/', '/api/conversations/', '/api/messages/'],
                'allowed_methods': ['GET', 'POST'],
                'denied_paths': ['/admin/', '/api/admin/']
            }
        }

    def __call__(self, request):
        # Skip authentication check for public endpoints
        if self._is_public_endpoint(request.path):
            return self.get_response(request)
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'code': 'authentication_required'
            }, status=401)
        
        # Check role-based access
        user_role = getattr(request.user, 'role', 'user')
        
        if not self._has_access(user_role, request.path, request.method):
            logger.warning(
                f"Access denied for user {request.user.username} (role: {user_role}) "
                f"to {request.method} {request.path}"
            )
            return JsonResponse({
                'error': 'Insufficient permissions for this action',
                'required_role': self._get_required_role(request.path, request.method),
                'current_role': user_role
            }, status=403)
        
        return self.get_response(request)

    def _is_public_endpoint(self, path):
        """Check if the endpoint is publicly accessible"""
        public_paths = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/auth/token/refresh/',
            '/admin/login/',
            '/api/health/',
        ]
        return any(path.startswith(public_path) for public_path in public_paths)

    def _has_access(self, user_role, path, method):
        """Check if user has access based on role configuration"""
        config = self.role_config.get(user_role, self.default_config.get(user_role, {}))
        
        # Check denied paths first
        denied_paths = config.get('denied_paths', [])
        if any(path.startswith(denied_path) for denied_path in denied_paths):
            return False
        
        # Check denied methods
        denied_methods = config.get('denied_methods', [])
        if method in denied_methods:
            return False
        
        # Check allowed paths
        allowed_paths = config.get('allowed_paths', [])
        if '*' in allowed_paths:
            return True
        
        # Check if path matches any allowed pattern
        path_access = any(path.startswith(allowed_path) for allowed_path in allowed_paths)
        
        # Check allowed methods
        allowed_methods = config.get('allowed_methods', [])
        method_access = method in allowed_methods if allowed_methods else True
        
        return path_access and method_access

    def _get_required_role(self, path, method):
        """Determine required role for a given path and method"""
        for role, config in self.default_config.items():
            if self._has_access(role, path, method):
                return role
        return 'admin'


class MaintenanceModeMiddleware:
    """
    Middleware to enable maintenance mode for the application
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)
        
        if maintenance_mode and not self._is_maintenance_exception(request):
            return JsonResponse({
                'error': 'Service temporarily unavailable for maintenance',
                'estimated_recovery_time': getattr(settings, 'MAINTENANCE_ETA', '30 minutes')
            }, status=503)
        
        return self.get_response(request)

    def _is_maintenance_exception(self, request):
        """Check if request should be allowed during maintenance"""
        # Allow health checks and admin access
        if request.path in ['/api/health/', '/admin/']:
            return True
        
        # Allow authenticated admin users
        if (request.user.is_authenticated and 
            getattr(request.user, 'role', 'user') in ['admin', 'superuser']):
            return True
        
        return False