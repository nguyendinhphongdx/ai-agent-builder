"""User factory."""
from __future__ import annotations

import factory

from app.models.user import User


class UserFactory(factory.Factory):
    class Meta:
        model = User

    # Sequence keeps emails unique across one test run without coordination.
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    is_active = True
    is_verified = False
    role = "user"
    # bcrypt-shaped placeholder — looks like a real hash so any code path
    # that inspects format won't choke, but verification will always fail
    # (which is what we want for unauthenticated test users).
    hashed_password = "$2b$12$" + "a" * 53
    token_version = 0
    stripe_charges_enabled = False
    stripe_payouts_enabled = False
