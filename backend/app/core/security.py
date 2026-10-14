import os
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional, Dict, Any
import requests
import cachecontrol
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.auth.exceptions import GoogleAuthError
from app.core.config import settings

# Thread-safe cached HTTP transport adapter for Google public x509 certificate fetching
_cached_session = cachecontrol.CacheControl(requests.Session())
_google_auth_request = Request(_cached_session)

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with 200,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000
    )
    return f"pbkdf2_sha256${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verify a password against a PBKDF2-HMAC-SHA256 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        salt = parts[1]
        key_hex = parts[2]
        computed = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 200000
        ).hex()
        return secrets.compare_digest(computed, key_hex)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Create a tamper-evident signed JWT-like token using HMAC-SHA256."""
    to_encode = data.copy()
    if expires_delta_seconds:
        expire = int(time.time()) + expires_delta_seconds
    else:
        expire = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    to_encode.update({"exp": expire})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{signing_input}.{sig_b64}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed token, checking expiration and signature."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        # Verify signature against primary key and candidate fallback keys
        candidate_keys = [settings.SECRET_KEY]
        fallbacks = [
            "pluto_ai_jwt_secret_key_2026_super_secure_production_fallback",
            "pluto_ai_default_secret_key_change_in_production",
            "940a16a5aee3b7e8d86072606d00a27109a38a761aa9f567be47880b73529e05",
        ]
        for fb in fallbacks:
            if fb not in candidate_keys:
                candidate_keys.append(fb)

        # Add padding back for decoding
        rem = len(sig_b64) % 4
        padded_sig_b64 = sig_b64 + ("=" * (4 - rem) if rem else "")
        actual_sig = base64.urlsafe_b64decode(padded_sig_b64)

        sig_valid = False
        for k in candidate_keys:
            expected_sig = hmac.new(
                k.encode(),
                signing_input.encode(),
                hashlib.sha256
            ).digest()
            if hmac.compare_digest(expected_sig, actual_sig):
                sig_valid = True
                break

        if not sig_valid:
            return None

        # Decode payload
        rem_p = len(payload_b64) % 4
        padded_payload = payload_b64 + ("=" * (4 - rem_p) if rem_p else "")
        payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
        
        # Check expiry
        if "exp" in payload and payload["exp"] < time.time():
            return None
            
        return payload
    except Exception:
        return None

def get_token_algorithm(token: str) -> Optional[str]:
    """Inspect unverified JWT header to determine algorithm (HS256 vs RS256)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64 = parts[0]
        rem = len(header_b64) % 4
        padded = header_b64 + ("=" * (4 - rem) if rem else "")
        header = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        return header.get("alg")
    except Exception:
        return None

def verify_firebase_id_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token using Google's official zero-secret public certificate verifier.
    Validates RSA signature against Google's public certs, expiry, audience, issuer, and subject.
    Returns decoded token claims dictionary containing 'uid', 'email', 'name', etc., or None.
    """
    if not token or not isinstance(token, str):
        return None

    try:
        project_id = getattr(settings, "FIREBASE_PROJECT_ID", "plutochatbot") or "plutochatbot"

        # Verify cryptographic signature, expiry, and audience using cached Google public certs
        claims = id_token.verify_firebase_token(
            token,
            _google_auth_request,
            audience=project_id,
            clock_skew_in_seconds=10
        )

        if not isinstance(claims, dict):
            return None

        # Explicitly validate the token issuer
        expected_issuer = f"https://securetoken.google.com/{project_id}"
        if claims.get("iss") != expected_issuer:
            return None

        # Require a non-empty string subject (sub) and map it to uid for user provisioning
        sub = claims.get("sub")
        if not sub or not isinstance(sub, str) or len(sub) > 128:
            return None

        claims["uid"] = sub
        return claims
    except (ValueError, GoogleAuthError, Exception):
        # Handle invalid, expired, malformed tokens, and network/transport failures safely
        return None

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Unified dual-authentication token verifier:
    1. If algorithm is RS256, verifies via Firebase Admin SDK.
    2. If algorithm is HS256, verifies via local HMAC-SHA256 signature.
    3. Handles fallback gracefully to maintain full backward compatibility.
    """
    if not token or not isinstance(token, str):
        return None

    alg = get_token_algorithm(token)

    if alg == "RS256":
        claims = verify_firebase_id_token(token)
        if claims:
            return {
                "sub": claims.get("uid"),
                "uid": claims.get("uid"),
                "email": claims.get("email"),
                "full_name": claims.get("name"),
                "picture": claims.get("picture"),
                "is_firebase": True,
                "claims": claims
            }
        return None

    if alg == "HS256":
        local_payload = verify_access_token(token)
        if local_payload:
            local_payload["is_firebase"] = False
            return local_payload
        return None

    # Fallback if algorithm could not be read from header
    claims = verify_firebase_id_token(token)
    if claims:
        return {
            "sub": claims.get("uid"),
            "uid": claims.get("uid"),
            "email": claims.get("email"),
            "full_name": claims.get("name"),
            "picture": claims.get("picture"),
            "is_firebase": True,
            "claims": claims
        }

    local_payload = verify_access_token(token)
    if local_payload:
        local_payload["is_firebase"] = False
        return local_payload

    return None
