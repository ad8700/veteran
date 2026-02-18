"""
AuthManager - Handles Cognito authentication for the Veteran Grave Marker app

Supports:
- Google Sign-In (OAuth)
- Email/Password sign-up and sign-in
- Guest access (unauthenticated)
"""
import json
import os
import base64
import hashlib
import secrets
from urllib.parse import urlencode, parse_qs, urlparse

from kivy.network.urlrequest import UrlRequest
from kivy.utils import platform
from kivy.clock import Clock

from utils.config import (
    AWS_REGION, USER_POOL_ID, USER_POOL_CLIENT_ID,
    IDENTITY_POOL_ID, COGNITO_DOMAIN, REDIRECT_URI
)


class AuthManager:
    """
    Manages user authentication with AWS Cognito.
    """

    def __init__(self):
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.user_info = None
        self.is_guest = False  # Start as not guest - require explicit choice
        self.has_chosen = False  # Track if user has made auth choice
        self._code_verifier = None

        # Load saved tokens
        self._load_tokens()

    def _get_token_path(self):
        """Get path for storing auth tokens"""
        from kivy.app import App
        app = App.get_running_app()
        if app:
            return os.path.join(app.user_data_dir, 'auth_tokens.json')
        return None

    def _load_tokens(self):
        """Load saved tokens from disk"""
        try:
            token_path = self._get_token_path()
            if token_path and os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.id_token = data.get('id_token')
                    self.refresh_token = data.get('refresh_token')
                    self.user_info = data.get('user_info')
                    self.is_guest = data.get('is_guest', False)
                    self.has_chosen = data.get('has_chosen', False)
                    self._code_verifier = data.get('code_verifier')
                    print(f"Loaded auth tokens, is_guest={self.is_guest}, has_chosen={self.has_chosen}")
        except Exception as e:
            print(f"Error loading tokens: {e}")

    def _save_tokens(self):
        """Save tokens to disk"""
        try:
            token_path = self._get_token_path()
            if token_path:
                data = {
                    'access_token': self.access_token,
                    'id_token': self.id_token,
                    'refresh_token': self.refresh_token,
                    'user_info': self.user_info,
                    'is_guest': self.is_guest,
                    'has_chosen': self.has_chosen,
                    'code_verifier': self._code_verifier
                }
                with open(token_path, 'w') as f:
                    json.dump(data, f)
        except Exception as e:
            print(f"Error saving tokens: {e}")

    def _clear_tokens(self):
        """Clear all tokens"""
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.user_info = None
        self.is_guest = True

        token_path = self._get_token_path()
        if token_path and os.path.exists(token_path):
            os.remove(token_path)

    def is_authenticated(self):
        """Check if user is authenticated (not guest)"""
        return not self.is_guest and self.access_token is not None

    def get_user_display_name(self):
        """Get display name for current user"""
        if self.is_guest:
            return "Guest"
        if self.user_info:
            return self.user_info.get('name', self.user_info.get('email', 'User'))
        return "User"

    def get_user_id(self):
        """Get user ID for API calls"""
        if self.is_guest:
            return 'guest'
        if self.user_info:
            return self.user_info.get('sub', 'unknown')
        return 'unknown'

    # ========== Google Sign-In ==========

    def _generate_pkce(self):
        """Generate PKCE code verifier and challenge for OAuth"""
        # Generate random code verifier
        self._code_verifier = secrets.token_urlsafe(32)

        # Create code challenge (SHA256 hash, base64url encoded)
        digest = hashlib.sha256(self._code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

        return code_challenge

    def get_google_sign_in_url(self):
        """Get the URL for Google Sign-In via Cognito Hosted UI"""
        code_challenge = self._generate_pkce()

        # Save the code verifier in case app is killed during OAuth
        self._save_tokens()

        params = {
            'client_id': USER_POOL_CLIENT_ID,
            'response_type': 'code',
            'scope': 'email openid profile',
            'redirect_uri': REDIRECT_URI,
            'identity_provider': 'Google',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        url = f"{COGNITO_DOMAIN}/oauth2/authorize?{urlencode(params)}"
        print(f"Generated Google Sign-In URL with code_verifier saved")
        return url

    def handle_oauth_callback(self, callback_url, on_success=None, on_error=None):
        """Handle OAuth callback URL and exchange code for tokens"""
        try:
            print(f"=== AuthManager: Handling OAuth callback ===")
            print(f"URL: {callback_url}")

            parsed = urlparse(callback_url)
            print(f"Parsed scheme: {parsed.scheme}, netloc: {parsed.netloc}, query: {parsed.query}")

            params = parse_qs(parsed.query)
            print(f"Query params: {list(params.keys())}")

            if 'error' in params:
                error = params.get('error_description', params.get('error', ['Unknown error']))[0]
                print(f"OAuth error: {error}")
                if on_error:
                    on_error(error)
                return

            if 'code' not in params:
                print("No authorization code in callback URL")
                if on_error:
                    on_error("No authorization code received")
                return

            auth_code = params['code'][0]
            print(f"Got authorization code: {auth_code[:20]}...")

            if not self._code_verifier:
                print("ERROR: No code_verifier available!")
                if on_error:
                    on_error("Session expired - please try signing in again")
                return

            print(f"Using code_verifier: {self._code_verifier[:20]}...")
            self._exchange_code_for_tokens(auth_code, on_success, on_error)

        except Exception as e:
            print(f"Error in handle_oauth_callback: {e}")
            import traceback
            traceback.print_exc()
            if on_error:
                on_error(str(e))

    def _exchange_code_for_tokens(self, auth_code, on_success=None, on_error=None):
        """Exchange authorization code for tokens"""
        token_url = f"{COGNITO_DOMAIN}/oauth2/token"
        print(f"=== Exchanging code for tokens ===")
        print(f"Token URL: {token_url}")

        body = urlencode({
            'grant_type': 'authorization_code',
            'client_id': USER_POOL_CLIENT_ID,
            'code': auth_code,
            'redirect_uri': REDIRECT_URI,
            'code_verifier': self._code_verifier
        })
        print(f"Request body: grant_type=authorization_code, client_id={USER_POOL_CLIENT_ID[:10]}...")

        def handle_response(req, result):
            print(f"=== Token response received ===")
            print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            try:
                self.access_token = result.get('access_token')
                self.id_token = result.get('id_token')
                self.refresh_token = result.get('refresh_token')
                self.is_guest = False
                self.has_chosen = True

                # Get user info
                self._get_user_info(on_success, on_error)

            except Exception as e:
                print(f"Error processing token response: {e}")
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(str(e)), 0)

        def handle_error(req, error):
            print(f"=== Token exchange error ===")
            print(f"Error: {error}")
            print(f"Request: {req}")
            if on_error:
                Clock.schedule_once(lambda dt: on_error(str(error)), 0)

        def handle_failure(req, result):
            print(f"=== Token exchange failure ===")
            print(f"Result: {result}")
            if on_error:
                Clock.schedule_once(lambda dt: on_error(f"Token exchange failed: {result}"), 0)

        print("Sending token request...")
        UrlRequest(
            token_url,
            req_body=body,
            req_headers={'Content-Type': 'application/x-www-form-urlencoded'},
            on_success=handle_response,
            on_error=handle_error,
            on_failure=handle_failure,
            method='POST'
        )

    def _get_user_info(self, on_success=None, on_error=None):
        """Get user info from Cognito"""
        userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"

        def handle_response(req, result):
            self.user_info = result
            self._save_tokens()
            print(f"Signed in as: {self.get_user_display_name()}")
            if on_success:
                Clock.schedule_once(lambda dt: on_success(self.user_info), 0)

        def handle_error(req, error):
            # Still save tokens even if userinfo fails
            self._save_tokens()
            if on_success:
                Clock.schedule_once(lambda dt: on_success({}), 0)

        UrlRequest(
            userinfo_url,
            req_headers={'Authorization': f'Bearer {self.access_token}'},
            on_success=handle_response,
            on_error=handle_error,
            on_failure=handle_error,
            method='GET'
        )

    # ========== Email/Password Sign-In ==========

    def sign_up(self, email, password, name=None, on_success=None, on_error=None):
        """Sign up with email and password"""
        url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/"

        body = json.dumps({
            'ClientId': USER_POOL_CLIENT_ID,
            'Username': email,
            'Password': password,
            'UserAttributes': [
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': name or email.split('@')[0]}
            ]
        })

        def handle_response(req, result):
            print(f"Sign up successful for {email}")
            if on_success:
                Clock.schedule_once(lambda dt: on_success(result), 0)

        def handle_error(req, error):
            error_msg = self._parse_cognito_error(error)
            if on_error:
                Clock.schedule_once(lambda dt: on_error(error_msg), 0)

        UrlRequest(
            url,
            req_body=body,
            req_headers={
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.SignUp'
            },
            on_success=handle_response,
            on_error=handle_error,
            on_failure=handle_error,
            method='POST'
        )

    def confirm_sign_up(self, email, code, on_success=None, on_error=None):
        """Confirm sign up with verification code"""
        url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/"

        body = json.dumps({
            'ClientId': USER_POOL_CLIENT_ID,
            'Username': email,
            'ConfirmationCode': code
        })

        def handle_response(req, result):
            print(f"Email confirmed for {email}")
            if on_success:
                Clock.schedule_once(lambda dt: on_success(result), 0)

        def handle_error(req, error):
            error_msg = self._parse_cognito_error(error)
            if on_error:
                Clock.schedule_once(lambda dt: on_error(error_msg), 0)

        UrlRequest(
            url,
            req_body=body,
            req_headers={
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.ConfirmSignUp'
            },
            on_success=handle_response,
            on_error=handle_error,
            on_failure=handle_error,
            method='POST'
        )

    def sign_in(self, email, password, on_success=None, on_error=None):
        """Sign in with email and password"""
        url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/"

        body = json.dumps({
            'AuthFlow': 'USER_PASSWORD_AUTH',
            'ClientId': USER_POOL_CLIENT_ID,
            'AuthParameters': {
                'USERNAME': email,
                'PASSWORD': password
            }
        })

        def handle_response(req, result):
            try:
                auth_result = result.get('AuthenticationResult', {})
                self.access_token = auth_result.get('AccessToken')
                self.id_token = auth_result.get('IdToken')
                self.refresh_token = auth_result.get('RefreshToken')
                self.is_guest = False
                self.has_chosen = True

                # Decode user info from ID token
                self._decode_id_token()
                self._save_tokens()

                print(f"Signed in as: {self.get_user_display_name()}")
                if on_success:
                    Clock.schedule_once(lambda dt: on_success(self.user_info), 0)

            except Exception as e:
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(str(e)), 0)

        def handle_error(req, error):
            error_msg = self._parse_cognito_error(error)
            if on_error:
                Clock.schedule_once(lambda dt: on_error(error_msg), 0)

        UrlRequest(
            url,
            req_body=body,
            req_headers={
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            on_success=handle_response,
            on_error=handle_error,
            on_failure=handle_error,
            method='POST'
        )

    def _decode_id_token(self):
        """Decode user info from ID token (JWT)"""
        if not self.id_token:
            return

        try:
            # JWT has 3 parts separated by dots
            parts = self.id_token.split('.')
            if len(parts) != 3:
                return

            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded = base64.urlsafe_b64decode(payload)
            self.user_info = json.loads(decoded)

        except Exception as e:
            print(f"Error decoding ID token: {e}")

    def _parse_cognito_error(self, error):
        """Parse Cognito error response"""
        try:
            if isinstance(error, dict):
                return error.get('message', str(error))
            if isinstance(error, str):
                try:
                    err_data = json.loads(error)
                    return err_data.get('message', error)
                except:
                    return error
            return str(error)
        except:
            return "Authentication error"

    # ========== Guest Access ==========

    def continue_as_guest(self, on_success=None):
        """Continue without signing in"""
        self._clear_tokens()
        self.is_guest = True
        self.has_chosen = True
        self._save_tokens()
        print("Continuing as guest")
        if on_success:
            Clock.schedule_once(lambda dt: on_success(), 0)

    # ========== Sign Out ==========

    def sign_out(self, on_complete=None):
        """Sign out the current user"""
        self._clear_tokens()
        print("Signed out")
        if on_complete:
            Clock.schedule_once(lambda dt: on_complete(), 0)


# Global instance
_auth_manager = None


def get_auth_manager():
    """Get or create the global AuthManager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
