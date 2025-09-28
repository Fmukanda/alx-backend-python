# apps/core/middleware/validation.py
import json
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class JSONValidationMiddleware:
    """
    Middleware to validate and modify incoming JSON payloads
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_content_length = 10 * 1024 * 1024  # 10MB

    def __call__(self, request):
        # Only process JSON content
        if (request.method in ['POST', 'PUT', 'PATCH'] and 
            request.content_type == 'application/json'):
            
            # Check content length
            content_length = request.META.get('CONTENT_LENGTH', 0)
            if int(content_length or 0) > self.max_content_length:
                return JsonResponse({
                    'error': 'Payload too large',
                    'max_size': f'{self.max_content_length} bytes'
                }, status=413)
            
            # Parse and validate JSON
            try:
                if request.body:
                    json_data = json.loads(request.body.decode('utf-8'))
                    request.json_data = self._validate_and_clean_json(json_data, request)
                else:
                    request.json_data = {}
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {str(e)}")
                return JsonResponse({
                    'error': 'Invalid JSON format',
                    'details': str(e)
                }, status=400)
            except ValidationError as e:
                logger.warning(f"JSON validation failed: {str(e)}")
                return JsonResponse({
                    'error': 'JSON validation failed',
                    'details': str(e)
                }, status=400)
        
        response = self.get_response(request)
        return response

    def _validate_and_clean_json(self, json_data, request):
        """
        Validate and clean JSON payload based on endpoint and method
        """
        # Remove null values and empty strings
        cleaned_data = self._remove_empty_values(json_data)
        
        # Validate based on endpoint
        endpoint_validation = self._get_endpoint_validation_rules(request.path, request.method)
        
        for field, rules in endpoint_validation.items():
            if field in cleaned_data:
                cleaned_data[field] = self._apply_validation_rules(cleaned_data[field], rules)
        
        return cleaned_data

    def _remove_empty_values(self, data):
        """Recursively remove null and empty string values"""
        if isinstance(data, dict):
            return {k: self._remove_empty_values(v) for k, v in data.items() if v not in [None, ""]}
        elif isinstance(data, list):
            return [self._remove_empty_values(item) for item in data if item not in [None, ""]]
        else:
            return data

    def _get_endpoint_validation_rules(self, path, method):
        """Get validation rules for specific endpoint and method"""
        rules = {
            '/api/messages/': {
                'POST': {
                    'message_body': {'max_length': 1000, 'strip': True},
                    'conversation': {'required': True, 'type': 'string'},
                    'message_type': {'allowed': ['text', 'image', 'file']}
                }
            },
            '/api/conversations/': {
                'POST': {
                    'participant_emails': {'type': 'list', 'max_items': 10},
                    'group_name': {'max_length': 100, 'strip': True},
                    'is_group': {'type': 'boolean'}
                }
            },
            '/api/auth/register/': {
                'POST': {
                    'email': {'type': 'email', 'required': True},
                    'password': {'min_length': 8, 'required': True},
                    'first_name': {'max_length': 50, 'strip': True},
                    'last_name': {'max_length': 50, 'strip': True}
                }
            }
        }
        
        endpoint_rules = rules.get(path, {})
        return endpoint_rules.get(method, {})

    def _apply_validation_rules(self, value, rules):
        """Apply validation rules to a value"""
        # Type validation
        if rules.get('type') == 'email' and isinstance(value, str):
            if '@' not in value:
                raise ValidationError(f"Invalid email format: {value}")
        
        elif rules.get('type') == 'boolean' and not isinstance(value, bool):
            if isinstance(value, str):
                if value.lower() in ['true', '1']:
                    return True
                elif value.lower() in ['false', '0']:
                    return False
            raise ValidationError(f"Expected boolean, got {type(value)}")
        
        # Length validation
        if isinstance(value, str):
            if 'max_length' in rules and len(value) > rules['max_length']:
                value = value[:rules['max_length']]
            
            if 'strip' in rules and rules['strip']:
                value = value.strip()
        
        return value


class ValidationError(Exception):
    """Custom validation error"""
    pass


class ContentSecurityMiddleware:
    """
    Middleware to add security headers and validate content types
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response

    def _add_security_headers(self, response):
        """Add security-related headers to response"""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }
        
        for header, value in security_headers.items():
            response[header] = value
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'; "
            "base-uri 'self';"
        )
        response['Content-Security-Policy'] = csp