import base64
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class CaldavMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Exclude the well-known endpoint from authentication
        if request.path == '/.well-known/caldav':
            return None  # Skip authentication for the well-known path

        # Apply authentication only to /caldav/ paths
        if request.path.startswith('/caldav/'):
            if request.method == 'OPTIONS':
                response = HttpResponse()
                response['Allow'] = 'OPTIONS, PROPFIND, GET'
                response['DAV'] = '1, 2, calendar-access'
                response['Content-Length'] = '0'
                return response

            if request.user.is_authenticated:
                return None

            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Basic '):
                try:
                    # Decode the base64-encoded credentials
                    auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                    username, password = auth_decoded.split(':', 1)
                    user = authenticate(request, username=username, password=password)
                    if user is not None:
                        login(request, user)  # Log the user in if authentication is successful
                        return None
                except ValueError:
                    pass

            # If authentication fails, return a 401 Unauthorized response
            response = HttpResponse('Unauthorized', status=401)
            response['WWW-Authenticate'] = 'Basic realm="CalDAV"'
            return response

        # If the request is for the root path (admin) or anything else, let the default behavior happen
        return None
