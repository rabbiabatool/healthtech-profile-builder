"""Production Settings Configuration (Week 6 Final Capstone).

Inherits from base settings and hardens all security flags:
- Enforces DEBUG=False
- Enforces HTTPS redirects (SECURE_SSL_REDIRECT)
- Secure cookie flags (Secure, HttpOnly, SameSite=Lax/Strict)
- Strict HTTP Strict Transport Security (HSTS) headers
- Content Security Policy & X-Content-Type-Options
"""
from __future__ import annotations

import os
from .settings import *  # noqa: F403

DEBUG = False

# Ensure secret key is strictly provided from environment in production
if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError("DJANGO_SECRET_KEY environment variable must be set in production!")

# HTTPS and SSL hardening
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookie Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
JWT_COOKIE_SECURE = True

# Browser Security Headers
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405 (1 year)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Production allowed hosts & CSRF trusted origins
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["healthtech.example.com", "localhost"])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["https://healthtech.example.com"])  # noqa: F405
