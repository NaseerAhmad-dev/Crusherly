"""Password hashing using Argon2id.

Never store plaintext passwords. `argon2-cffi`'s default `PasswordHasher` uses Argon2id.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the stored hash was created with weaker-than-current parameters."""
    return _hasher.check_needs_rehash(password_hash)
