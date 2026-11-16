from drf_spectacular.extensions import OpenApiAuthenticationExtension


class MemberJwtCookieScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "memberJwtCookie"
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": "Short-lived JWT set by POST /api/auth/user/login as an HttpOnly cookie.",
        }


class AdminSessionCookieScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.AdminSessionAuthentication"
    name = "adminSessionCookie"
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "admin_session",
            "description": "Server-side session set by POST /api/admin/login as an HttpOnly cookie.",
        }
