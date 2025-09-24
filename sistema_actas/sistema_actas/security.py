from django.conf import settings
from django.http import HttpResponseForbidden
import logging
import re
from datetime import datetime, timedelta
from django.core.cache import cache

logger = logging.getLogger('security')

class SecurityMiddleware:
    """Midleware de seguridad personalizado"""
    def __init__(self, get_response):
        self.get_response = get_response
        
        #Patrones de ataques comunes
        self.attack_patterns = [
            r'<script.*?>.*?</script>',
            r'union.*select',
            r'javascript:',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'eval\s*\(',
            r'exec\s*\(',
        ]
        
        #IPs bloqueadas temporalemnte
        self.blocked_ips = set()
    
    def __call__(self, request):
        #verificar Ip bloqueada
        if self.is_ip_blocked(request):
            logger.warning(f"Blocked Ip attempt: {self.get_client_ip(request)}")
            return HttpResponseForbidden("Access denied")
        
        #Verificar patrones de ataque en parametros
        if self.detect_attack_patterns(request):
            self.block_ip_temporarily(request)
            logger.critical(f"Attack pattern detected from IP: {self.get_client_ip(request)}")
            return HttpResponseForbidden("Malicious request detected")
        
        #Verificar rate limiting
        if self.is_rate_limited(request):
            logger.warning(f"Rate limit exceeded for IP: {self.get_client_ip(request)}")
            return  HttpResponseForbidden("Rate limit exceeded")
        
        response = self.get_response(request)
        
        #Agregar header de seguridad
        response ['X-Content-Type-options'] = 'nosniff'
        response ['X-Frame-Options'] = 'DENY'
        response ['X-XSS-Protection'] = '1; mode=block'
        response ['Referrer-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        if settings.DEBUG is False:
            response ['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response
    
    def get_client_ip(self, request):
        """Obtener IP real del cliente"""
        
        x_forwarded_for = request.META.get ('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            ip = x_forwarded_for.split(',') [0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def detect_attack_patterns (self,request):
        """Detectar patrones de ataque en la request"""
        #Verificar parametros GET
        for key, value in request.GET.items ():
            if self.contains_attack_pattern(value):
                return True
            
        #verificae parametros POST
        for key, value in request.POST.items ():
            if self.contains_attack_pattern (str(value)):
                return True
            
        #Verificar headers sospechosos
        user_agent = request.META.get ('HTTP_USER_AGENT', '')
        if self.contains_attack_pattern(user_agent):
            return True
        
        return False
    
    def contains_attack_pattern (self,text):
        """Verificar si el texto contiene patrones de ataque"""
        text = text.lower ()
        for pattern in self.attack_patterns:
            if re.search (pattern, text, re.IGNORECASE):
                return True
        return False
    
    def is_ip_blocked (self, request):
        """Verificar si la IP esta bloqueada"""
        ip = self.get_client_ip(request)
        return cache.get(f"blocked_ip_{ip}", False)
    
    def block_ip_temporarily(self, request, duration=3600):
        """Bloquear IP temporalmente (1 hora por defecto)"""
        ip = self.get_client_ip(request)
        cache.set (f"blocked_ip_{ip}", True, duration)
        
    def is_rate_limited(self, request):
        """Verificar rate limiting"""
        ip = self.get_client_ip(request)
        key = f"rate_limit_{ip}"
        
        # Obtener contador actual
        requests = cache.get(key, 0)
        
        # Límite: 100 requests por minuto
        if requests >= 100:
            return True
        
        # Incrementar contador
        cache.set(key, requests + 1, 60)  # 60 segundos
        return False

class AuditLogMiddleware:
    """Middleware para logging de auditoria"""
    def __init__(self, get_response):
        self.get_response = get_response
        self.audit_logger = logging.getLogger('audit')
        
    def __call__(self, request):
        start_time = datetime.now()
        
        response = self.get_response (request)
        
        #Log de acciones importantes
        if self.should_audit (request):
            duration = datetime.now() - start_time
            
            self.audit_logger.info({
                'user': getattr (request.user, 'email', 'anonymous'),
                'ip': self.get_client_ip(request),
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': duration.total_seconds () * 1000,
                'user_agent': request.META.get ('HTTP_USER_AGENT', ''),
                'timestamp': start_time.isoformat (),
            })
            
            return response
    def should_audit(self, request):
        """Determinar si la request debe ser auditada"""
        #Audotar todas las acciones POST, PUT, DELETE
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return True
        
        #Auditar accesos a rutas sensibles
        
        sensitive_paths = {
            '/admin/',
            '/api/',
            '/actas/',
            '/accounts/',
        }
        
        for path in sensitive_paths:
            if request.path.startswith(path):
                return True
        return False
    
    def get_cliente_ip (self,request):
        """Obtener Ip real del cliente"""
        x_forwarded_for = request.META.get ('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            ip = x_forwarded_for.split(',') [0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip