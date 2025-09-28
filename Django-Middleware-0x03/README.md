# Middleware Documentation

## Overview
This project uses a comprehensive middleware stack for request processing, security, and monitoring.

## Middleware Order
1. **CORS Middleware** - Handle cross-origin requests
2. **Security Middleware** - Basic security features
3. **Request Logging** - Log all incoming requests
4. **IP Blocking** - Block banned IPs and suspicious sources
5. **Rate Limiting** - Prevent API abuse
6. **JSON Validation** - Validate and clean JSON payloads
7. **Role-Based Access** - Authorization based on user roles
8. **Maintenance Mode** - Enable maintenance mode
9. **Security Headers** - Add security headers to responses

## Configuration
Each middleware can be configured via Django settings:

- `BANNED_IPS`: List of IPs to block
- `RATE_LIMITS`: Rate limiting configuration
- `ROLE_ACCESS_CONFIG`: Role-based access rules
- `MAINTENANCE_MODE