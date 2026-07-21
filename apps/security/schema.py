from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Registers apps.security.authentication.CustomJWTAuthentication for
    drf-spectacular. Without this, drf-spectacular is unaware of JWTAuthentication.
    """

    target_class = "apps.security.authentication.CustomJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
