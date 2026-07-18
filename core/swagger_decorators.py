from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers


class CustomJWTSwaggerScheme(OpenApiAuthenticationExtension):
    """
    Tells drf-spectacular that CustomJWTAuthentication is a standard JWT Bearer token setup.
    This fixes the 'could not resolve authenticator' warnings.
    """

    target_class = "apps.security.authentication.CustomJWTAuthentication"
    name = "BearerAuth"  # Matches the scheme name in your settings.py

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }


def document_cookie_auth(
    behavior: str, request_serializer=None, response_serializer=None
):
    """
    A custom decorator for automating the documentation of Cookie-JWT endpoints.
    """
    if behavior == "register":
        return extend_schema(
            summary="User registration",
            description="Creates an account. Returns the access token in JSON and \
                        places the refresh token in an HttpOnly cookie.",
            request=request_serializer,
            auth=[],  # A registration token is not required.
            responses={
                201: OpenApiResponse(
                    response=response_serializer,
                    description=f"The user has been created, and the refresh_token \
                                has been sent in the Set-Cookie header.",
                )
            },
        )

    elif behavior == "login":
        return extend_schema(
            summary="System Login (Authorization)",
            description="Authentication via email and password. Returns an access token in JSON format \
                        and stores the refresh token in an HttpOnly cookie.",
            auth=[],
            responses={
                200: OpenApiResponse(
                    description="Successful login. The refresh_token has been saved to the browser cookies.",
                    response=inline_serializer(
                        name="LoginCleanResponse",
                        fields={
                            "access": serializers.CharField(
                                help_text="JWT Access Token"
                            )
                        },
                    ),
                )
            },
        )

    elif behavior == "refresh":
        return extend_schema(
            summary="Access token update (Refresh)",
            description="Expects a valid refresh_token in an HttpOnly cookie. Returns a new access token.",
            request=None,  # The request body is empty.
            auth=[{"CookieAuth": []}],  # Requires cookie
            responses={
                200: OpenApiResponse(
                    description="Access token successfully updated.",
                    response=inline_serializer(
                        name="RefreshCleanResponse",
                        fields={
                            "access": serializers.CharField(
                                help_text="New JWT Access Token"
                            )
                        },
                    ),
                ),
                401: OpenApiResponse(
                    description="The refresh_token cookie is missing or invalid."
                ),
            },
        )

    elif behavior == "logout":
        return extend_schema(
            summary="Log out (Logout)",
            description="Adds the current refresh token to the blacklist, resets \
                        the user's token version, and deletes the cookie.",
            request=None,
            responses={
                200: OpenApiResponse(
                    description="Successful exit. The hook has been removed."
                )
            },
        )


def custom_permission_description_hook(result, generator, **kwargs):
    """
    Global post-processing hook for drf-spectacular.
    Uses target view reflection to map permissions directly into the OpenAPI dictionary.
    """
    # 1. Сначала строим карту: operationId -> список пермишенов
    operation_permissions = {}

    # generator.endpoints возвращает готовые обработанные эндпоинты
    endpoints = generator.endpoints

    for path, path_regex, method, view in endpoints:
        permissions = getattr(view, "permission_classes", [])
        if not permissions:
            continue

        # Заставляем схему вьюхи сгенерировать точный operationId для данного метода
        auto_schema = getattr(view, "schema", None)
        if auto_schema:
            auto_schema.method = method.lower()
            try:
                operation_id = auto_schema.get_operation_id()
                operation_permissions[operation_id] = permissions
            except Exception:
                continue

    # 2. Проходим по финальной JSON-схеме и обновляем описания
    for path, methods in result.get("paths", {}).items():
        for method_name, operation in methods.items():
            operation_id = operation.get("operationId")

            if operation_id in operation_permissions:
                extra_notes = []
                for perm in operation_permissions[operation_id]:
                    perm_name = (
                        perm.__name__
                        if hasattr(perm, "__name__")
                        else perm.__class__.__name__
                    )

                    if perm_name == "IsTenant":
                        extra_notes.append(
                            "🛑 **Access Restriction:** Allowed only for users in the **Tenant** group."
                        )
                    elif perm_name == "IsLandlord":
                        extra_notes.append(
                            "🛑 **Access Restriction:** Allowed only for users in the **Landlord** group."
                        )
                    elif perm_name == "IsModerator":
                        extra_notes.append(
                            "🛑 **Access Restriction:** Allowed only for users in the **Moderator** group."
                        )
                    elif perm_name == "IsAdmin":
                        extra_notes.append(
                            "🛑 **Access Restriction:** Restricted to system **Admins** or **Superusers**."
                        )
                    elif perm_name == "IsOwner":
                        extra_notes.append(
                            "🔐 **Access Restriction:** Access granted exclusively to the **Object Owner**."
                        )

                if extra_notes:
                    current_desc = operation.get("description", "")
                    new_desc = (
                        current_desc + "\n\n" + "\n".join(extra_notes)
                        if current_desc
                        else "\n".join(extra_notes)
                    )
                    operation["description"] = new_desc.strip()

    return result
