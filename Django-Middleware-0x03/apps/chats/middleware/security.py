# apps/core/middleware/security.py
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
import logging
import time
import re

logger = logging.getLogger(__name__)

class IPBlockingMiddleware:
    """
    Middleware to block requests from banned IPs or suspicious sources
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.banned_ips = set(getattr(settings, 'BANNED_IPS', []))
        self.suspicious_headers = getattr(settings, 'SUSPICIOUS_HEADERS', {})
        
        # Patterns for suspicious user agents
        self.suspicious_user_agents = [
            r'bot', r'crawler', r'spider', r'scanner', 
            r'sqlmap', r'nmap', r'nikto', r'metasploit'
        ]

    def __call__(self, request):
        client_ip = self._get_client_ip(request)
        
        # Check if IP is banned
        if self._is_banned_ip(client_ip):
            logger.warning(f"Blocked request from banned IP: {client_ip}")
            return JsonResponse({
                'error': 'Access denied',
                'code': 'ip_blocked'
            }, status=403)
        
        # Check for suspicious headers
        if self._has_suspicious_headers(request):
            logger.warning(f"Suspicious headers detected from IP: {client_ip}")
            self._block_ip_temporarily(client_ip)
            return JsonResponse({
                'error': 'Suspicious activity detected',
                'code': 'suspicious_headers'
            }, status=403)
        
        # Check for suspicious user agent
        if self._has_suspicious_user_agent(request):
            logger.warning(f"Suspicious user agent from IP: {client_ip}")
            return JsonResponse({
                'error': 'Access denied',
                'code': 'suspicious_user_agent'
            }, status=403)
        
        return self.get_response(request)

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

    def _is_banned_ip(self, ip):
        """Check if IP is in banned list"""
        return ip in self.banned_ips or cache.get(f'banned_ip_{ip}')

    def _has_suspicious_headers(self, request):
        """Check for suspicious HTTP headers"""
        for header, pattern in self.suspicious_headers.items():
            header_value = request.META.get(header, '')
            if re.search(pattern, header_value, re.IGNORECASE):
                return True
        return False

    def _has_suspicious_user_agent(self, request):
        """Check for suspicious User-Agent strings"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for pattern in self.suspicious_user_agents:
            if re.search(pattern, user_agent):
                return True
        return False

    def _block_ip_temporarily(self, ip, duration=3600):
        """Temporarily block an IP address"""
        cache.set(f'banned_ip_{ip}', True, duration)


class RateLimitingMiddleware:
    """
    Advanced rate limiting middleware with IP-based and user-based limits
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = getattr(settings, 'RATE_LIMITS', {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'auth': {'requests': 5, 'window': 300},       # 5 auth attempts per 5 minutes
            'messages': {'requests': 10, 'window': 60},   # 10 messages per minute
            'api': {'requests': 1000, 'window': 3600},    # 1000 API calls per hour
        })

    def __call__(self, request):
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.user, 'id', None) if request.user.is_authenticated else None
        
        # Determine rate limit type based on request
        limit_type = self._get_rate_limit_type(request)
        limit_config = self.rate_limits.get(limit_type, self.rate_limits['default'])
        
        # Create cache key
        if user_id:
            cache_key = f"rate_limit_{limit_type}_user_{user_id}"
        else:
            cache_key = f"rate_limit_{limit_type}_ip_{client_ip}"
        
        # Check rate limit
        if not self._check_rate_limit(cache_key, limit_config):
            logger.warning(
                f"Rate limit exceeded for {limit_type} - "
                f"IP: {client_ip}, User: {user_id}"
            )
            
            retry_after = self._get_retry_after(cache_key, limit_config)
            
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'limit_type': limit_type,
                'retry_after': retry_after,
                'limits': limit_config
            }, status=429)
        
        response = self.get_response(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, cache_key, limit_config)
        
        return response

    def _get_rate_limit_type(self, request):
        """Determine the appropriate rate limit type for the request"""
        path = request.path
        
        if path.startswith('/api/auth/'):
            return 'auth'
        elif path.startswith('/api/messages/') and request.method == 'POST':
            return 'messages'
        elif path.startswith('/api/'):
            return 'api'
        else:
            return 'default'

    def _check_rate_limit(self, cache_key, limit_config):
        """Check if request is within rate limits"""
        current = cache.get(cache_key, {'count': 0, 'window_start': time.time()})
        window_start = current['window_start']
        current_time = time.time()
        
        # Reset if window has expired
        if current_time - window_start > limit_config['window']:
            current = {'count': 1, 'window_start': current_time}
        else:
            current['count'] += 1
        
        # Update cache
        cache.set(cache_key, current, limit_config['window'])
        
        return current['count'] <= limit_config['requests']

    def _get_retry_after(self, cache_key, limit_config):
        """Calculate retry-after time in seconds"""
        current = cache.get(cache_key)
        if current:
            time_passed = time.time() - current['window_start']
            return max(1, int(limit_config['window'] - time_passed))
        return limit_config['window']

    def _add_rate_limit_headers(self, response, cache_key, limit_config):
        """Add rate limit headers to response"""
        current = cache.get(cache_key, {'count': 0, 'window_start': time.time()})
        
        response['X-RateLimit-Limit'] = str(limit_config['requests'])
        response['X-RateLimit-Remaining'] = str(max(0, limit_config['requests'] - current['count']))
        response['X-RateLimit-Reset'] = str(int(current['window_start'] + limit_config['window']))

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')