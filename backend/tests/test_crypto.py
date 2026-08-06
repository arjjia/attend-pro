from cryptography.hazmat.primitives.asymmetric import ec

from app.security import (
    PortalSigner,
    canonical_json,
    public_jwk,
    verify_es256,
)


def test_rfc8785_canonicalization_is_independent_of_property_order():
    left = {"z": 1, "a": {"я": True, "b": [3, 2, 1]}}
    right = {"a": {"b": [3, 2, 1], "я": True}, "z": 1}
    assert canonical_json(left) == canonical_json(right)


def test_portal_uses_persistent_p256_key_and_raw_webcrypto_signature(tmp_path):
    key_path = tmp_path / "portal.pem"
    first = PortalSigner(str(key_path), "test-key")
    payload = {"version": "test.v1", "message": "подписано"}
    signature = first.sign(payload)
    assert len(signature) == 86
    assert verify_es256(first.public_jwk, payload, signature)
    assert not verify_es256(first.public_jwk, {**payload, "message": "подменено"}, signature)

    second = PortalSigner(str(key_path), "test-key")
    assert second.public_jwk == first.public_jwk
    assert second.verify(payload, signature)
    assert "d" not in public_jwk(ec.generate_private_key(ec.SECP256R1()).public_key())
