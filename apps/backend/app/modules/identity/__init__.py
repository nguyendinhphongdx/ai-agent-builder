"""identity/ — WHO can act on the platform.

  * auth/        login + JWT/session + OAuth login + MFA + SSO + SCIM
  * workspaces/  multi-tenant boundary (workspace + member + invitation + IP rules)
  * tokens/      personal access tokens (API auth, no cookie)

Note: ``auth/`` absorbs MFA/SSO/SCIM because they're all "ways a user
proves identity to the platform" — keeps the protocol-stack picture
in one place.

External-service OAuth (Slack/Notion/Dropbox connections) is NOT here
— see ``modules/integrations/connectors/oauth/``.
"""
