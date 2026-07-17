from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers


def document_cookie_auth(behavior: str, request_serializer=None, response_serializer=None):
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
                                has been sent in the Set-Cookie header."
                )
            }
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
                        name='LoginCleanResponse',
                        fields={'access': serializers.CharField(help_text="JWT Access Token")}
                    )
                )
            }
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
                        name='RefreshCleanResponse',
                        fields={'access': serializers.CharField(help_text="New JWT Access Token")}
                    )
                ),
                401: OpenApiResponse(description="The refresh_token cookie is missing or invalid.")
            }
        )

    elif behavior == "logout":
        return extend_schema(
            summary="Log out (Logout)",
            description="Adds the current refresh token to the blacklist, resets \
                        the user's token version, and deletes the cookie.",
            request=None,
            responses={
                200: OpenApiResponse(description="Successful exit. The hook has been removed.")
            }
        )