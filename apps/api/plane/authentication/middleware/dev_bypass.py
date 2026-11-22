# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.utils import timezone

from plane.db.models import Profile, User, Workspace, WorkspaceMember
from plane.license.models import Instance

DEV_USER_EMAIL = "local-dev@plane.test"
DEV_USER_USERNAME = "local-dev"


def _ensure_local_development_user():
    user, created = User.objects.get_or_create(
        email=DEV_USER_EMAIL,
        defaults={
            "username": DEV_USER_USERNAME,
            "display_name": "Local Developer",
            "first_name": "Local",
            "last_name": "Developer",
            "is_email_verified": True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    if not user.is_active:
        raise RuntimeError("The local development user is inactive.")

    workspace = Workspace.objects.filter(owner=user, deleted_at__isnull=True).order_by("created_at").first()
    if workspace is None:
        workspace_slug = f"local-dev-{user.id.hex[:8]}"
        workspace, _ = Workspace.objects.get_or_create(
            slug=workspace_slug,
            defaults={"name": "Local Development", "owner": user},
        )
        if workspace.owner_id != user.id:
            raise RuntimeError(f"The local development workspace slug '{workspace_slug}' is already in use.")

    member = WorkspaceMember.objects.filter(
        workspace=workspace,
        member=user,
        deleted_at__isnull=True,
    ).first()
    if member is None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=20, is_active=True)
    elif not member.is_active or member.role != 20:
        member.is_active = True
        member.role = 20
        member.save(update_fields=["is_active", "role"])

    onboarding_step = {
        "profile_complete": True,
        "workspace_create": True,
        "workspace_invite": True,
        "workspace_join": True,
    }
    profile, _ = Profile.objects.get_or_create(user=user)
    profile_updates = []
    for field, value in (
        ("is_onboarded", True),
        ("onboarding_step", onboarding_step),
        ("last_workspace_id", workspace.id),
    ):
        if getattr(profile, field) != value:
            setattr(profile, field, value)
            profile_updates.append(field)
    if profile_updates:
        profile.save(update_fields=profile_updates)

    instance = Instance.objects.first()
    if instance is None:
        Instance.objects.create(
            instance_name="Plane Local Development",
            instance_id="local-development",
            current_version="local-development",
            last_checked_at=timezone.now(),
            is_setup_done=True,
            is_verified=True,
            is_telemetry_enabled=False,
            is_support_required=False,
            is_test=True,
        )
    elif not instance.is_setup_done:
        instance.is_setup_done = True
        instance.save(update_fields=["is_setup_done"])

    return user


class LocalDevelopmentAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.LOCAL_DEV_AUTH_BYPASS
            and request.path.startswith("/api/")
            and not getattr(getattr(request, "user", None), "is_authenticated", False)
        ):
            request.user = _ensure_local_development_user()

        return self.get_response(request)
