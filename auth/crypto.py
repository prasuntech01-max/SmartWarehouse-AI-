"""Authentication utilities for Module 12.
Provides secure password hashing using scrypt and constant‑time verification.
All functions operate on raw password strings and return/accept bytes.
"""

import hashlib
import os
import hmac
from typing import Tuple

# Default scrypt parameters – cost can be increased later via config.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_SIZE = 16  # 128‑bit salt


def hash_password(password: str, *, salt: bytes | None = None) -> bytes:
    """Hash a plaintext password using scrypt.

    Returns ``salt || hash || params`` encoded as ``bytes``.
    The layout is:
        16‑byte salt | 64‑byte derived key | 4‑byte N | 4‑byte r | 4‑byte p
    All integers are little‑endian.
    """
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    if salt is None:
        salt = os.urandom(_SALT_SIZE)
    elif len(salt) != _SALT_SIZE:
        raise ValueError("invalid salt length")
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=64,
    )
    # pack parameters for future re‑hash checks
    params = _SCRYPT_N.to_bytes(4, "little") + _SCRYPT_R.to_bytes(4, "little") + _SCRYPT_P.to_bytes(4, "little")
    return salt + dk + params


def verify_password(stored: bytes, password: str) -> bool:
    """Verify a password against a stored hash.
    ``stored`` must be the output of :func:`hash_password`.
    """
    if len(stored) < 16 + 64 + 12:
        raise ValueError("stored hash is malformed")
    salt = stored[:16]
    stored_dk = stored[16:80]
    params = stored[80:]
    n = int.from_bytes(params[0:4], "little")
    r = int.from_bytes(params[4:8], "little")
    p = int.from_bytes(params[8:12], "little")
    try:
        test_dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=64,
        )
    except ValueError:
        # scrypt params invalid – treat as failed verification
        return False
    return hmac.compare_digest(stored_dk, test_dk)


def needs_rehash(stored: bytes, *, target_n: int = _SCRYPT_N, target_r: int = _SCRYPT_R, target_p: int = _SCRYPT_P) -> bool:
    """Return ``True`` if the stored hash uses weaker parameters than the target.
    The caller may then re‑hash the password on next successful login.
    """
    if len(stored) < 80 + 12:
        return True
    params = stored[80:]
    n = int.from_bytes(params[0:4], "little")
    r = int.from_bytes(params[4:8], "little")
    p = int.from_bytes(params[8:12], "little")
    return n < target_n or r < target_r or p < target_p
