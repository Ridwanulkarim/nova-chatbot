import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional, Dict, Any
from app.core.config import settings

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
        
        # Verify signature
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        
        # Add padding back for decoding
        rem = len(sig_b64) % 4
        padded_sig_b64 = sig_b64 + ("=" * (4 - rem) if rem else "")
        actual_sig = base64.urlsafe_b64decode(padded_sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
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
