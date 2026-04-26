"""
Thin wrappers around passlib so the rest of the codebase
doesn't import from passlib directly.
"""
from __future__ import annotations

from passlib.context import CryptContext

# Cost 12: ~130ms on a 2-vCPU box — safe against brute-force, still snappy for users.
_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Return a bcrypt-12 hash of *plain*."""
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    return _ctx.verify(plain, hashed)
