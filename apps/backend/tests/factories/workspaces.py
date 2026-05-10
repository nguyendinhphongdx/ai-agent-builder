"""Organization + Workspace + WorkspaceMember + WorkspaceInvitation factories."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import factory

from app.models.organization import ORG_PLAN_FREE, Organization
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import WORKSPACE_ROLE_OWNER, WorkspaceMember


class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")
    slug = factory.Sequence(lambda n: f"org-{n}")
    billing_email = factory.LazyAttribute(lambda obj: f"billing+{obj.slug}@example.com")
    plan = ORG_PLAN_FREE
    settings = factory.LazyFunction(dict)


class WorkspaceFactory(factory.Factory):
    class Meta:
        model = Workspace

    # ``organization_id`` is set by the test (or via SubFactory in higher-
    # level factories). We don't auto-create an Organization here because
    # ``factory.Factory`` can't persist — the test must add+flush both.
    organization_id = None
    name = factory.Sequence(lambda n: f"Workspace {n}")
    slug = factory.Sequence(lambda n: f"ws-{n}")
    is_personal = False
    settings = factory.LazyFunction(dict)


class WorkspaceMemberFactory(factory.Factory):
    class Meta:
        model = WorkspaceMember

    workspace_id = None
    user_id = None
    role = WORKSPACE_ROLE_OWNER
    invited_by = None


class WorkspaceInvitationFactory(factory.Factory):
    class Meta:
        model = WorkspaceInvitation

    workspace_id = None
    email = factory.Sequence(lambda n: f"invitee{n}@example.com")
    role = "editor"
    token = factory.Sequence(lambda n: f"invite-token-{n:032d}")
    expires_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
    accepted_at = None
    invited_by = None
