from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.users.models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "username" in self.fields:
            del self.fields["username"]


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "username" in self.fields:
            del self.fields["username"]


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = (
        "email",
        "nickname",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "nickname", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal data",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "nickname",
                    "gender",
                    "phone",
                    "contact_phone",
                    "avatar",
                )
            },
        ),
        (
            "Statuses and access rights",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Platform blocks and settings",
            {
                "fields": (
                    "blocked_reason",
                    "blocked_by",
                    "notify_by_email",
                    "terms_accepted_at",
                )
            },
        ),
        ("Lifecycle dates", {"fields": ("date_joined", "updated_at", "deleted_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("updated_at",)
