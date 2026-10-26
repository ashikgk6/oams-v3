import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import get_settings

settings = get_settings()

_KNOWN_QR_ERRORS = {
    "Unknown kiosk",
    "Bad signature",
    "QR expired — scan again",
}


def _b64e(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return urlsafe_b64decode(data + pad)


def sign_qr_payload(kiosk_id: int, kiosk_secret: str) -> tuple[str, int]:
    ttl = settings.qr_ttl_seconds
    body = {
        "kid": kiosk_id,
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + ttl,
    }
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    key = f"{settings.qr_hmac_secret}:{kiosk_secret}".encode()
    sig = hmac.new(key, raw, hashlib.sha256).digest()
    return f"{_b64e(raw)}.{_b64e(sig)}", ttl


def verify_qr_token(token: str, lookup_secret) -> dict:
    """Validate HMAC QR. `lookup_secret(kiosk_id)` returns the device secret or None."""
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64d(raw_b64)
        sig = _b64d(sig_b64)
        body = json.loads(raw.decode())
        kiosk_id = int(body["kid"])
        secret = lookup_secret(kiosk_id)
        if not secret:
            raise ValueError("Unknown kiosk")
        key = f"{settings.qr_hmac_secret}:{secret}".encode()
        expected = hmac.new(key, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Bad signature")
        if int(body["exp"]) < int(time.time()):
            raise ValueError("QR expired — scan again")
        return body
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc) in _KNOWN_QR_ERRORS:
            raise
        raise ValueError("Invalid QR token") from exc


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_display_token() -> str:
    return secrets.token_urlsafe(32)


def generate_pair_code() -> str:
    return secrets.token_hex(3).upper()


def generate_device_secret() -> str:
    return secrets.token_urlsafe(24)
