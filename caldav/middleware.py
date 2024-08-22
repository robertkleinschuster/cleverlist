import base64
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class BasicAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Only apply this middleware to URLs that start with /caldav/
        if not request.path.startswith('/caldav/'):
            return None  # Skip middleware for other paths

        if request.user.is_authenticated:
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Basic '):
            try:
                # Decode the base64-encoded credentials
                auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = auth_decoded.split(':', 1)
                user = authenticate(request, username=username, password=password)
                if user:
                    request.user = user
                    return None
            except ValueError:
                pass

        # If authentication fails, return a 401 Unauthorized response
        response = HttpResponse('Unauthorized', status=401)
        response['WWW-Authenticate'] = 'Basic realm="CalDAV"'
        return response
