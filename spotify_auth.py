#!/usr/bin/env python3
"""
spotify_auth.py - Spotify OAuth Authentication Manager for Tamil Discography.
Supports interactive OAuth 2.0 Authorization Code flow with automatic localhost
callback capture, token persistence, auto-refresh, and fallback mechanisms.
"""

import base64
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TOKEN_FILE = Path(__file__).parent / ".spotify_tokens.json"
LOCAL_ENV = Path(__file__).parent / ".env"
SONGSTORE_ENV = Path("/home/nandha/Desktop/songstore/.env")

# Default Client Credentials
DEFAULT_CLIENT_ID = "d1ef45dc97564e9080283f6c76ee28aa"
DEFAULT_CLIENT_SECRET = "afc050f7148d46ddbebc25c4211096d4"
DEFAULT_REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "user-read-private user-read-email playlist-read-private playlist-modify-public playlist-modify-private"

def parse_env_file(path: Path):
    vals = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        vals[k.strip()] = v.strip().strip('"').strip("'")
        except Exception as e:
            logging.warning(f"Failed to read {path}: {e}")
    return vals

def load_env_credentials():
    """Load client credentials from local .env, environment, or songstore .env."""
    local_vals = parse_env_file(LOCAL_ENV)
    songstore_vals = parse_env_file(SONGSTORE_ENV)

    cid = os.getenv("SPOTIFY_CLIENT_ID") or local_vals.get("SPOTIFY_CLIENT_ID") or songstore_vals.get("SPOTIFY_CLIENT_ID") or DEFAULT_CLIENT_ID
    csec = os.getenv("SPOTIFY_CLIENT_SECRET") or local_vals.get("SPOTIFY_CLIENT_SECRET") or songstore_vals.get("SPOTIFY_CLIENT_SECRET") or DEFAULT_CLIENT_SECRET
    ruri = os.getenv("SPOTIFY_REDIRECT_URI") or local_vals.get("SPOTIFY_REDIRECT_URI") or songstore_vals.get("SPOTIFY_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    return cid, csec, ruri


class SpotifyOAuthServer(BaseHTTPRequestHandler):
    auth_code = None
    error_msg = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if "code" in query:
            SpotifyOAuthServer.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Spotify Connected</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                           background: #121212; color: #ffffff; text-align: center; padding-top: 80px; }
                    .card { background: #181818; max-width: 480px; margin: 0 auto; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
                    h1 { color: #1DB954; font-size: 28px; margin-bottom: 12px; }
                    p { color: #b3b3b3; font-size: 16px; line-height: 1.5; }
                    .badge { display: inline-block; background: #1DB954; color: #000; font-weight: bold; padding: 8px 20px; border-radius: 20px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Spotify Account Connected!</h1>
                    <p>Your authentication was successful. Your account is now linked to the Tamil Songs cataloger.</p>
                    <div class="badge">You can close this tab now</div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        elif "error" in query:
            SpotifyOAuthServer.error_msg = query["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h1>Authorization Failed: {SpotifyOAuthServer.error_msg}</h1>".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence default HTTP server access logs
        pass


class SpotifyAuthManager:
    def __init__(self, token_file=TOKEN_FILE, redirect_uri=None):
        self.token_file = Path(token_file)
        self.client_id, self.client_secret, default_ruri = load_env_credentials()
        self.redirect_uri = redirect_uri or default_ruri
        self.tokens = self._load_tokens()

    def _load_tokens(self):
        if self.token_file.exists():
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load {self.token_file}: {e}")
        return None

    def _save_tokens(self, tokens_data):
        self.tokens = tokens_data
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                json.dump(tokens_data, f, indent=2)
            os.chmod(self.token_file, 0o600)
            logging.info(f"Saved Spotify tokens to {self.token_file}")
        except Exception as e:
            logging.error(f"Failed to save tokens: {e}")

    def get_auth_url(self):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": SCOPES,
            "show_dialog": "true"
        }
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    def exchange_code(self, code):
        """Exchange authorization code for access and refresh tokens."""
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=data,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_resp = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logging.error(f"Token exchange failed ({e.code}): {error_body}")
            raise RuntimeError(f"Spotify token exchange failed: {error_body}")

        expires_at = time.time() + token_resp.get("expires_in", 3600) - 60
        access_token = token_resp["access_token"]
        refresh_token = token_resp.get("refresh_token")

        # Fetch user profile to verify and save metadata
        profile = self.fetch_user_profile(access_token)

        tokens_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "token_type": token_resp.get("token_type", "Bearer"),
            "scope": token_resp.get("scope", SCOPES),
            "user": profile,
            "auth_type": "oauth_user"
        }
        self._save_tokens(tokens_data)
        return tokens_data

    def refresh_token(self):
        """Use refresh_token to acquire a fresh access_token."""
        if not self.tokens or not self.tokens.get("refresh_token"):
            raise RuntimeError("No refresh token available. Re-authentication required.")

        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.tokens["refresh_token"]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=data,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            token_resp = json.loads(resp.read().decode("utf-8"))

        self.tokens["access_token"] = token_resp["access_token"]
        self.tokens["expires_at"] = time.time() + token_resp.get("expires_in", 3600) - 60
        if "refresh_token" in token_resp:
            self.tokens["refresh_token"] = token_resp["refresh_token"]

        self._save_tokens(self.tokens)
        logging.info("Successfully refreshed Spotify access token.")
        return self.tokens["access_token"]

    def fetch_user_profile(self, access_token):
        """Fetch current authorized user's profile info."""
        req = urllib.request.Request(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "id": data.get("id"),
                    "display_name": data.get("display_name"),
                    "email": data.get("email"),
                    "country": data.get("country"),
                    "product": data.get("product"),
                    "uri": data.get("uri"),
                    "spotify_url": data.get("external_urls", {}).get("spotify")
                }
        except Exception as e:
            logging.warning(f"Could not fetch user profile: {e}")
            return {}

    def get_valid_token(self):
        """Return a valid access token, auto-refreshing if expired."""
        if not self.tokens or "access_token" not in self.tokens:
            raise RuntimeError("Spotify account not connected. Please run interactive login.")

        if time.time() >= self.tokens.get("expires_at", 0):
            logging.info("Token expired. Refreshing...")
            return self.refresh_token()

        return self.tokens["access_token"]

    def is_connected(self):
        """Check if active connection exists."""
        if not self.tokens or "access_token" not in self.tokens:
            return False
        try:
            token = self.get_valid_token()
            return bool(token)
        except Exception:
            return False

    def connect_interactive(self, timeout=300):
        """
        Start local server on localhost:8888, open browser, and wait for callback.
        """
        SpotifyOAuthServer.auth_code = None
        SpotifyOAuthServer.error_msg = None

        parsed_uri = urllib.parse.urlparse(self.redirect_uri)
        port = parsed_uri.port or 8888
        server = HTTPServer(("127.0.0.1", port), SpotifyOAuthServer)
        server.timeout = 2.0

        auth_url = self.get_auth_url()
        print("\n" + "="*70, flush=True)
        print("          SPOTIFY ACCOUNT AUTHORIZATION", flush=True)
        print("="*70, flush=True)
        print("Opening Spotify login in your browser...", flush=True)
        print(f"\nIf it does not open automatically, copy & paste this link:", flush=True)
        print(f"\n{auth_url}\n", flush=True)
        print("="*70 + "\n", flush=True)

        # Open in browser
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logging.warning(f"Could not auto-open browser: {e}")

        start_time = time.time()
        print("Waiting for you to log in and approve in the browser (timeout: 5m)...", flush=True)
        
        while time.time() - start_time < timeout:
            server.handle_request()
            if SpotifyOAuthServer.auth_code:
                break
            if SpotifyOAuthServer.error_msg:
                server.server_close()
                raise RuntimeError(f"User denied or Spotify returned error: {SpotifyOAuthServer.error_msg}")

        server.server_close()

        if not SpotifyOAuthServer.auth_code:
            raise TimeoutError("Interactive login timed out after 120 seconds.")

        print("\nAuthorization code received! Exchanging for access token...")
        tokens = self.exchange_code(SpotifyOAuthServer.auth_code)
        
        user = tokens.get("user", {})
        print("\n" + "="*70)
        print("          SPOTIFY ACCOUNT CONNECTED SUCCESSFULLY! ")
        print("="*70)
        print(f"User Name:    {user.get('display_name', 'N/A')}")
        print(f"User ID:      {user.get('id', 'N/A')}")
        print(f"Account Type: {user.get('product', 'N/A').capitalize()}")
        print(f"Country:      {user.get('country', 'N/A')}")
        print(f"Profile URL:  {user.get('spotify_url', 'N/A')}")
        print("="*70 + "\n")
        return tokens


if __name__ == "__main__":
    manager = SpotifyAuthManager()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        if manager.is_connected():
            u = manager.tokens.get("user", {})
            print(f"CONNECTED: {u.get('display_name')} ({u.get('id')}) - {u.get('product')}")
        else:
            print("NOT CONNECTED")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "--url":
        print(manager.get_auth_url())
        sys.exit(0)

    if len(sys.argv) > 2 and sys.argv[1] == "--code":
        code = sys.argv[2]
        print(f"Exchanging manual code: {code[:15]}...")
        tokens = manager.exchange_code(code)
        u = tokens.get("user", {})
        print(f"SUCCESS: Connected as {u.get('display_name')} ({u.get('id')})")
        sys.exit(0)

    if len(sys.argv) > 2 and sys.argv[1] == "--callback":
        cb_url = sys.argv[2]
        parsed = urllib.parse.urlparse(cb_url)
        query = urllib.parse.parse_qs(parsed.query)
        if "code" not in query:
            print(f"Error: No code found in callback URL: {cb_url}")
            sys.exit(1)
        code = query["code"][0]
        tokens = manager.exchange_code(code)
        u = tokens.get("user", {})
        print(f"SUCCESS: Connected as {u.get('display_name')} ({u.get('id')})")
        sys.exit(0)

    try:
        manager.connect_interactive()
    except Exception as e:
        logging.error(f"Failed to connect Spotify account: {e}")
        sys.exit(1)

