# apps/core/tests/test_middleware.py
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from apps.core.middleware.authentication import RoleBasedAccessMiddleware
from apps.core.middleware.security import IPBlockingMiddleware
from apps.core.middleware.validation import JSONValidationMiddleware
import json

class MiddlewareTests(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.role = 'user'  # Add role attribute
        
    def test_role_based_access_middleware(self):
        """Test role-based access control"""
        middleware = RoleBasedAccessMiddleware(lambda req: None)
        
        # Test authenticated user access
        request = self.factory.get('/api/conversations/')
        request.user = self.user
        
        response = middleware(request)
        self.assertIsNone(response)  # Should allow access
        
        # Test unauthenticated user
        request.user.is_authenticated = False
        response = middleware(request)
        self.assertEqual(response.status_code, 401)
    
    def test_json_validation_middleware(self):
        """Test JSON validation middleware"""
        middleware = JSONValidationMiddleware(lambda req: None)
        
        # Test valid JSON
        request = self.factory.post(
            '/api/messages/',
            data=json.dumps({'message_body': 'Hello'}),
            content_type='application/json'
        )
        
        response = middleware(request)
        self.assertIsNone(response)
        
        # Test invalid JSON
        request = self.factory.post(
            '/api/messages/',
            data='invalid json',
            content_type='application/json'
        )
        
        response = middleware(request)
        self.assertEqual(response.status_code, 400)
    
    def test_ip_blocking_middleware(self):
        """Test IP blocking functionality"""
        middleware = IPBlockingMiddleware(lambda req: None)
        
        # Test allowed IP
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        response = middleware(request)
        self.assertIsNone(response)

# apps/core/tests/test_views.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

class MiddlewareIntegrationTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        
    def test_rate_limiting(self):
        """Test rate limiting middleware"""
        # Make multiple rapid requests
        for i in range(6):
            response = self.client.post('/api/auth/login/', {
                'email': 'test@example.com',
                'password': 'password'
            })
            
            if i >= 5:  # Should be rate limited
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    def test_security_headers(self):
        """Test security headers are present"""
        response = self.client.get('/api/health/')
        
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)
        self.assertIn('Content-Security-Policy', response)