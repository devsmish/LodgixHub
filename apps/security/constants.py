GROUP_TENANT = "tenant"
GROUP_LANDLORD = "landlord"
GROUP_MODERATOR = "moderator"
GROUP_ADMIN = "admin"

SYSTEM_ROLES = [
    GROUP_TENANT,
    GROUP_LANDLORD,
    GROUP_MODERATOR,
    GROUP_ADMIN,
]

JWT_MIDDLEWARE_EXCLUDED_PATHS = {
    "/api/v1/auth/register/",
    "/api/v1/auth/login/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/token/refresh/",
}
JWT_MIDDLEWARE_EXCLUDED_PATH_PREFIXES = ("/admin/",)
