# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from plane.authentication.middleware.dev_bypass import LocalDevelopmentAuthMiddleware
from plane.db.models import Profile, User, WorkspaceMember
from plane.license.models import Instance


@pytest.mark.unit
@pytest.mark.django_db
class TestLocalDevelopmentAuthMiddleware:
    def test_enabled_api_bypass_bootstraps_user_workspace_and_instance(self):
        request = RequestFactory().get("/api/users/me/")
        middleware = LocalDevelopmentAuthMiddleware(lambda req: HttpResponse())

        with override_settings(LOCAL_DEV_AUTH_BYPASS=True):
            middleware(request)

        user = User.objects.get(email="local-dev@plane.test")
        profile = Profile.objects.get(user=user)
        membership = WorkspaceMember.objects.get(member=user)

        assert request.user == user
        assert request.user.is_authenticated
        assert profile.is_onboarded
        assert profile.last_workspace_id == membership.workspace_id
        assert membership.is_active
        assert membership.role == 20
        assert Instance.objects.get().is_setup_done

    def test_bypass_is_inactive_when_disabled_or_for_non_api_paths(self):
        middleware = LocalDevelopmentAuthMiddleware(lambda req: HttpResponse())
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with override_settings(LOCAL_DEV_AUTH_BYPASS=True):
            middleware(request)

        assert not request.user.is_authenticated
        assert not User.objects.filter(email="local-dev@plane.test").exists()

        request = RequestFactory().get("/api/users/me/")
        request.user = AnonymousUser()
        with override_settings(LOCAL_DEV_AUTH_BYPASS=False):
            middleware(request)

        assert not request.user.is_authenticated
        assert not User.objects.filter(email="local-dev@plane.test").exists()
