from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from jwt import InvalidTokenError

from app.config import get_settings


ALGORITHM = "ES256"
CURVE = "P-256"


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def isoformat_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_json(value: Any) -> bytes:
    return rfc8785.dumps(value)


def canonical_digest(value: Any) -> str:
    return b64url_encode(hashlib.sha256(canonical_json(value)).digest())


def public_key_from_jwk(jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
    if jwk.get("kty") != "EC" or jwk.get("crv") != CURVE:
        raise ValueError("Only EC P-256 public keys are accepted")
    if jwk.get("ext") is False or "d" in jwk:
        raise ValueError("A public, extractable verification key is required")
    try:
        x_bytes = b64url_decode(jwk["x"])
        y_bytes = b64url_decode(jwk["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Malformed public JWK") from exc
    if len(x_bytes) != 32 or len(y_bytes) != 32:
        raise ValueError("P-256 coordinates must be 32 bytes")
    return ec.EllipticCurvePublicNumbers(
        int.from_bytes(x_bytes, "big"), int.from_bytes(y_bytes, "big"), ec.SECP256R1()
    ).public_key()


def public_jwk(key: ec.EllipticCurvePublicKey) -> dict[str, Any]:
    numbers = key.public_numbers()
    return {
        "kty": "EC",
        "crv": CURVE,
        "x": b64url_encode(numbers.x.to_bytes(32, "big")),
        "y": b64url_encode(numbers.y.to_bytes(32, "big")),
        "ext": True,
        "key_ops": ["verify"],
    }


def _der_to_raw(signature: bytes) -> bytes:
    r, s = decode_dss_signature(signature)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _raw_to_der(signature: bytes) -> bytes:
    if len(signature) != 64:
        raise ValueError("ES256 signature must be 64 bytes")
    return encode_dss_signature(
        int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    )


def verify_es256(public_jwk_value: dict[str, Any], payload: Any, signature: str) -> bool:
    try:
        public_key_from_jwk(public_jwk_value).verify(
            _raw_to_der(b64url_decode(signature)), canonical_json(payload), ec.ECDSA(hashes.SHA256())
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


class PortalSigner:
    def __init__(self, key_path: str, key_id: str) -> None:
        self.key_path = Path(key_path)
        self.key_id = key_id
        self._private_key = self._load_or_create()

    def _load_or_create(self) -> ec.EllipticCurvePrivateKey:
        if self.key_path.exists():
            loaded = serialization.load_pem_private_key(self.key_path.read_bytes(), password=None)
            if not isinstance(loaded, ec.EllipticCurvePrivateKey) or not isinstance(
                loaded.curve, ec.SECP256R1
            ):
                raise RuntimeError("Portal key must be an unencrypted P-256 private key")
            return loaded
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self.key_path.write_bytes(pem)
        self.key_path.chmod(0o600)
        return key

    @property
    def public_jwk(self) -> dict[str, Any]:
        return public_jwk(self._private_key.public_key())

    def sign(self, payload: Any) -> str:
        signature = self._private_key.sign(canonical_json(payload), ec.ECDSA(hashes.SHA256()))
        return b64url_encode(_der_to_raw(signature))

    def verify(self, payload: Any, signature: str) -> bool:
        return verify_es256(self.public_jwk, payload, signature)


@lru_cache
def get_portal_signer() -> PortalSigner:
    settings = get_settings()
    return PortalSigner(settings.portal_private_key_path, settings.portal_key_id)


def create_session_token(user_id: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "aud": "attendpro-web", "exp": expires_at},
        settings.session_secret,
        algorithm="HS256",
    )


def decode_session_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.session_secret, algorithms=["HS256"], audience="attendpro-web"
        )
        return str(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError) as exc:
        raise ValueError("Invalid authentication session") from exc
