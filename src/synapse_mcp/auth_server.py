"""
Core Authorization Server logic using Authlib, compliant with MCP specification."""
import logging
import time
import os
from authlib.oauth2.rfc6749 import grants, errors
from authlib.oauth2.rfc6749 import AuthorizationServer
from authlib.oauth2.rfc6749.resource_protector import ResourceProtector, TokenValidator
from authlib.jose import jwt, jwk
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route
import uuid
import secrets
from synapse_mcp import pat_auth_manager

db = {"clients": {}, "codes": {}, "auth_sessions": {}}

def get_keys():
    private_key_path = '/tmp/jwt_private.pem'
    public_key_path = '/tmp/jwt_public.pem'

    if not os.path.exists(private_key_path):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()))
        public_key = private_key.public_key()
        with open(public_key_path, 'wb') as f:
            f.write(public_key.public_bytes(encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo))
    with open(private_key_path, 'rb') as f:
        private_key_data = f.read()
    with open(public_key_path, 'rb') as f:
        public_key_data = f.read()
    return private_key_data, public_key_data

private_key, public_key = get_keys()

def query_client(client_id):
    client = db["clients"].get(client_id)
    if client:
        # Create a client object that Authlib expects
        class ClientObject:
            def __init__(self, client_data):
                for key, value in client_data.items():
                    setattr(self, key, value)

            def check_redirect_uri(self, redirect_uri):
                return redirect_uri in self.redirect_uris

            def has_client_secret(self):
                return bool(getattr(self, 'client_secret', ''))

            def check_client_secret(self, client_secret):
                return getattr(self, 'client_secret', '') == client_secret

            def check_token_endpoint_auth_method(self, method):
                return getattr(self, 'token_endpoint_auth_method', 'client_secret_post') == method

            def check_response_type(self, response_type):
                return response_type in getattr(self, 'response_types', ['code'])

            def check_grant_type(self, grant_type):
                return grant_type in getattr(self, 'grant_types', ['authorization_code'])

        return ClientObject(client)
    return None

def save_token(token, request):
    pass

class FastAPIAuthorizationServer(AuthorizationServer):
    def create_oauth2_request(self, request):
        """Convert FastAPI request to OAuth2 request"""
        from authlib.oauth2.rfc6749 import OAuth2Request
        from urllib.parse import urlencode

        # Get query parameters and form data
        query_params = dict(request.query_params) or {}
        if hasattr(request, '_form') and request._form:
            form_data = dict(request._form)
        else:
            form_data = {}

        # Create a custom OAuth2Request that properly handles query params
        class FastAPIOAuth2Request(OAuth2Request):
            def __init__(self, method, uri, body, headers, query_params, form_data):
                super().__init__(method, uri, body, headers)
                self._query_params = query_params
                self._form_data = form_data
                # Create a payload object that Authlib expects
                self.payload = self._create_payload()

            def _create_payload(self):
                """Create a payload object with request parameters"""
                class RequestPayload:
                    def __init__(self, query_params, form_data):
                        # Ensure we have dictionaries to work with
                        query_params = query_params or {}
                        form_data = form_data or {}

                        # Combine query params and form data
                        combined = {}
                        combined.update(query_params)
                        combined.update(form_data)

                        # Set attributes from the combined data
                        for key, value in combined.items():
                            setattr(self, key, value)

                        # Set default scope if not provided
                        if not hasattr(self, 'scope') or not self.scope:
                            self.scope = 'view modify download'

                        # Ensure we have client_id
                        if not hasattr(self, 'client_id'):
                            self.client_id = combined.get('client_id')

                        # Create datalist attribute for Authlib validation
                        # This is used to check for duplicate parameters
                        # It should be a dict where each key maps to a list of values
                        self.datalist = {}
                        for key, value in combined.items():
                            if key not in self.datalist:
                                self.datalist[key] = []
                            self.datalist[key].append(value)

                return RequestPayload(self._query_params, self._form_data)

            def __getattr__(self, name):
                # First check form data (for POST requests)
                if name in self._form_data:
                    return self._form_data[name]
                # Then check query parameters (for GET requests)
                if name in self._query_params:
                    return self._query_params[name]
                # Return None if not found
                return None

            @property
            def data(self):
                # Combine both query params and form data
                combined = {}
                combined.update(self._query_params)
                combined.update(self._form_data)
                return combined

            @property
            def form(self):
                # Return form data in the format Authlib expects
                return self._form_data

        # Create the body content
        if request.method == 'POST' and form_data:
            body = urlencode(form_data).encode()
        else:
            body = b''

        return FastAPIOAuth2Request(
            method=request.method,
            uri=str(request.url),
            body=body,
            headers=dict(request.headers),
            query_params=query_params,
            form_data=form_data
        )

    def handle_response(self, status, payload, headers):
        """Handle OAuth2 responses and convert to FastAPI responses"""
        from fastapi.responses import JSONResponse, RedirectResponse
        from urllib.parse import urlencode

        # Convert headers to dict if it's a list of tuples
        if isinstance(headers, list):
            headers_dict = dict(headers)
        else:
            headers_dict = headers or {}

        if status == 302:
            # This is a redirect response
            if 'Location' in headers_dict:
                return RedirectResponse(url=headers_dict['Location'], status_code=302)
            elif isinstance(payload, dict) and 'redirect_uri' in payload:
                # Build redirect URL with parameters
                redirect_uri = payload['redirect_uri']
                params = {k: v for k, v in payload.items() if k != 'redirect_uri'}
                if params:
                    redirect_uri += f"?{urlencode(params)}"
                return RedirectResponse(url=redirect_uri, status_code=302)

        # Default to JSON response
        return JSONResponse(content=payload, status_code=status, headers=headers_dict)

server = FastAPIAuthorizationServer()
server.query_client = query_client
server.save_token = save_token
class MyAuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ['client_secret_basic', 'client_secret_post', 'none']

    def save_authorization_code(self, code, request):
        auth_code = {
            "code": code, "client_id": request.client.client_id, "redirect_uri": request.redirect_uri,
            "scope": request.scope, "user": request.user, "nonce": request.data.get("nonce"),
            "code_challenge": request.data.get("code_challenge"), "code_challenge_method": request.data.get("code_challenge_method"),
            }
        db["codes"][code] = auth_code
        return code

    def query_authorization_code(self, code, client):
        auth_code = db["codes"].get(code)
        if auth_code and auth_code["client_id"] == client.client_id:
            # Create an authorization code object that Authlib expects
            class AuthorizationCodeObject:
                def __init__(self, code_data):
                    self.code_data = code_data
                    for key, value in code_data.items():
                        setattr(self, key, value)

                def get_redirect_uri(self):
                    return self.code_data.get("redirect_uri")

                def get_scope(self):
                    return self.code_data.get("scope")

                def is_expired(self):
                    # For simplicity, we'll say codes don't expire for now
                    return False

                def get_nonce(self):
                    return self.code_data.get("nonce")

            return AuthorizationCodeObject(auth_code)
        return None

    def delete_authorization_code(self, authorization_code):
        # Handle both dict and object formats
        if hasattr(authorization_code, 'code'):
            code = authorization_code.code
        else:
            code = authorization_code["code"]

        if code in db["codes"]:
            del db["codes"][code]

    def authenticate_user(self, authorization_code):
        # Handle both dict and object formats
        if hasattr(authorization_code, 'user'):
            return authorization_code.user
        else:
            return authorization_code["user"]

    def authenticate_token_endpoint_client(self):
        """Support clients with no authentication (method='none')"""
        try:
            # First try to get client_id from the request
            client_id = None
            if hasattr(self.request, 'payload') and self.request.payload:
                client_id = getattr(self.request.payload, 'client_id', None)

            if client_id:
                client = query_client(client_id)
                if client and hasattr(client, 'token_endpoint_auth_method') and client.token_endpoint_auth_method == 'none':
                    return client

            return super().authenticate_token_endpoint_client()
        except Exception as e:
            logging.error(f"Error in authenticate_token_endpoint_client: {e}")
            # Fallback: try to get client_id and look it up
            try:
                client_id = getattr(self.request.payload, 'client_id', None) if hasattr(self.request, 'payload') else None
                if client_id:
                    return query_client(client_id)
            except:
                pass
            return None


class JWTTokenValidator(TokenValidator):
    def __init__(self, public_key, realm=None, **kwargs):
        self.public_key = public_key
        self.realm = realm

    def authenticate_token(self, token_string):
        try:
            return jwt.decode(token_string, self.public_key)
        except Exception as e:
            logging.error(f"Token validation failed: {e}")
            return None

    def validate_token(self, token, scopes, request):
        if not token:
            raise errors.InvalidTokenError()
        return True


require_oauth = ResourceProtector()
require_oauth.register_token_validator(JWTTokenValidator(public_key))


async def require_mcp_auth(request: Request):
    """A hybrid authentication dependency that accepts either a spec-compliant JWT or the server's pre-configured Synapse Personal Access Token."""
    # First, try to validate as a JWT
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer ") and len(auth_header.split(" ")) > 1:
            token_str = auth_header.split(" ")[1]
            claims = jwt.decode(token_str, public_key)
            logging.info(f"Authenticated request using JWT for subject: {claims['sub']}")
            return claims
    except Exception:
        # This will fail if the token is not a valid JWT, which is expected for a PAT.
        pass

    # If JWT fails, check if it's the PAT
    if pat_auth_manager.synapse_client:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer ") and len(auth_header.split(" ")) > 1:
            token_str = auth_header.split(" ")[1]
            if token_str == os.environ.get("SYNAPSE_PAT"):
                logging.info(f"Authenticated request using SYNAPSE_PAT for user: {pat_auth_manager.user_profile.get('userName')}")
                return pat_auth_manager.user_profile

    # If both methods fail, return a spec-compliant 401 response
    server_url = get_http_server_url()
    metadata_url = f"{server_url}/.well-known/oauth-authorization-server"
    headers = {
        "WWW-Authenticate": f'mcp resource_metadata="{metadata_url}"' 
        }
    return Response(content='{"detail": "Authentication required"}', status_code=401, headers=headers, media_type="application/json")

def token_generator(client, grant_type, user, scope, **kwargs):
    header = {'alg': 'RS256'}
    payload = {
        'iss': get_http_server_url(),
        'sub': user.get('synapse_id', 'unknown'),
        'aud': client.client_id,
        'exp': int(time.time()) + 3600,
        'iat': int(time.time()),
        'scope': scope
    }
    token = jwt.encode(header, payload, private_key)

    # Ensure token is returned as string, not bytes
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return {
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': scope
    }

async def jwks_endpoint(request: Request):
    return JSONResponse({'keys': [jwk.dumps(public_key, kty='RSA')]})

def get_http_server_url():
    """Convert MCP_SERVER_URL from mcp:// to http:// scheme for OAuth endpoints."""
    mcp_url = os.environ.get("MCP_SERVER_URL", "mcp://localhost:9000")
    return mcp_url.replace("mcp://", "http://").replace("https://", "http://")

async def well_known_oauth_server(request: Request):
    server_url = get_http_server_url()
    metadata = {
        "issuer": server_url,
        "authorization_endpoint": f"{server_url}/authorize",
        "token_endpoint": f"{server_url}/token",
        "jwks_uri": f"{server_url}/jwks.json",
        "registration_endpoint": f"{server_url}/register",
        "scopes_supported": ["view", "modify", "download"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256"]
    }
    return JSONResponse(metadata)

async def well_known_oauth_protected_resource(request: Request):
    server_url = get_http_server_url()
    metadata = {
        "resource": f"{server_url}/mcp",
        "authorization_servers": [server_url],
        "jwks_uri": f"{server_url}/jwks.json",
        "scopes_supported": ["view", "modify", "download"]
    }
    return JSONResponse(metadata)

async def authorize(request: Request):
    try:
        logging.info(f"Authorization request: {dict(request.query_params)}")

        # Check if client exists
        client_id = request.query_params.get('client_id')
        client = query_client(client_id)
        if not client:
            logging.error(f"Client not found: {client_id}")
            return JSONResponse({"error": "invalid_client", "error_description": f"Client {client_id} not found"}, status_code=400)

        logging.info(f"Found client: {client.client_id}")

        # Validate redirect URI
        redirect_uri = request.query_params.get('redirect_uri')
        if not client.check_redirect_uri(redirect_uri):
            logging.error(f"Invalid redirect URI: {redirect_uri}")
            return JSONResponse({"error": "invalid_request", "error_description": "Invalid redirect_uri"}, status_code=400)

        grant = server.get_consent_grant(request=request, end_user=None)
        auth_session_id = str(uuid.uuid4())
        db["auth_sessions"][auth_session_id] = grant.request

        # Check if Synapse OAuth is configured
        if not os.environ.get("SYNAPSE_OAUTH_CLIENT_ID"):
            logging.error("SYNAPSE_OAUTH_CLIENT_ID not configured")
            return JSONResponse({"error": "server_error", "error_description": "OAuth not properly configured"}, status_code=500)

        from synapse_mcp.auth import SynapseAuth
        auth_helper = SynapseAuth()
        # Use the registered redirect URI from environment or default
        redirect_uri = os.environ.get("SYNAPSE_OAUTH_REDIRECT_URI", "http://127.0.0.1:9000/oauth/callback")
        # Pass the auth_session_id as the state parameter to link the sessions
        synapse_auth_url = auth_helper.get_oauth_url(
            client_id=os.environ["SYNAPSE_OAUTH_CLIENT_ID"],
            redirect_uri=redirect_uri,
            scope="view modify download",
            state=auth_session_id
        )
        return RedirectResponse(synapse_auth_url, status_code=302)
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Authorization error: {error_detail}")
        return JSONResponse({"error": "invalid_request", "error_description": str(e)}, status_code=400)

async def synapse_callback(request: Request):
    query_params = dict(request.query_params)
    code = query_params.get('code')
    state = query_params.get('state')

    auth_session = db["auth_sessions"].get(state)
    if not auth_session:
        return JSONResponse({"error": "Invalid session"}, status_code=400)
    user = {"synapse_id": f"synapse_user_{secrets.token_hex(4)}"}
    del db["auth_sessions"][state]
    original_request = auth_session
    return server.create_authorization_response(original_request, grant_user=user)

async def issue_token(request: Request):
    try:
        # Parse form data for POST requests
        if request.method == 'POST':
            form_data = dict(await request.form())
            request._form = form_data
            logging.info(f"Token request form data: {form_data}")
        return server.create_token_response(request)
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Token issue error: {error_detail}")
        return JSONResponse({"error": "invalid_request", "error_description": str(e)}, status_code=400)

async def register_client(request: Request):
    try:
        # Try to parse as JSON first, then fall back to form data
        try:
            data = await request.json()
        except:
            data = dict(await request.form())

        # Log the received data for debugging
        logging.info(f"Client registration data: {data}")

        # Handle redirect_uris field (could be string or list)
        redirect_uris = data.get("redirect_uris") or data.get("redirect_uri")
        if not redirect_uris:
            return JSONResponse({"error": "invalid_request", "error_description": "redirect_uris is required"}, status_code=400)

        # Convert to list if it's a string
        if isinstance(redirect_uris, str):
            redirect_uris = redirect_uris.split()
        elif not isinstance(redirect_uris, list):
            redirect_uris = [str(redirect_uris)]

        client_id = str(uuid.uuid4())
        # Use the auth method requested by the client, default to none for MCP clients
        auth_method = data.get("token_endpoint_auth_method", "none")

        client = {
            "client_id": client_id,
            "client_secret": secrets.token_urlsafe(32) if auth_method != "none" else "",
            "client_name": data.get("client_name"),
            "redirect_uris": redirect_uris,
            "scope": "view modify download",
            "token_endpoint_auth_method": auth_method,
            "grant_types": data.get("grant_types", ["authorization_code"]),
            "response_types": data.get("response_types", ["code"])
        }
        db["clients"][client_id] = client
        return JSONResponse({k: v for k, v in client.items() if k != 'client_secret'})
    except Exception as e:
        logging.error(f"Client registration error: {e}")
        return JSONResponse({"error": "invalid_request", "error_description": str(e)}, status_code=400)

# --- Export a list of routes to be added to the main app ---
server.register_grant(MyAuthorizationCodeGrant)
server.register_token_generator('default', token_generator)

auth_routes = [
    Route('/.well-known/oauth-authorization-server', endpoint=well_known_oauth_server, methods=['GET']),
    Route('/.well-known/oauth-authorization-server/mcp', endpoint=well_known_oauth_server, methods=['GET']),
    Route('/.well-known/oauth-protected-resource', endpoint=well_known_oauth_protected_resource, methods=['GET']),
    Route('/.well-known/oauth-protected-resource/mcp', endpoint=well_known_oauth_protected_resource, methods=['GET']),
    Route('/jwks.json', endpoint=jwks_endpoint, methods=['GET']),
    Route('/authorize', endpoint=authorize, methods=['GET', 'POST']),
    Route('/oauth/callback', endpoint=synapse_callback, methods=['GET']),
    Route('/token', endpoint=issue_token, methods=['POST']),
    Route('/register', endpoint=register_client, methods=['POST'])
]

