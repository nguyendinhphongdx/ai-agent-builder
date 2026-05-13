"""Auth subrouters — one file per sub-concern.

The parent :mod:`app.modules.identity.auth.router` aggregates them
under the ``/auth`` prefix. Adding a new auth-adjacent endpoint =
drop it into the existing subrouter that fits, or add a new one
here and wire it in the aggregator.

Split rationale (see docs/backend/module-template.md):

* ``basic``         — register / login / refresh / logout
* ``mfa_login``     — login-time MFA challenge (the second factor
                      verifier; full MFA setup lives in ``mfa/``)
* ``profile``       — /me read + edit + avatar + password change
* ``email``         — change primary email + initial verification
* ``password_reset``— public forgot / reset flow
"""
