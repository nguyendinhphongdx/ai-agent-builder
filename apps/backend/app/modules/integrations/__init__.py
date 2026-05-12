"""integrations/ — external systems we plug INTO.

  * connectors/oauth/  3-legged OAuth dance for Slack/Notion/Dropbox
                       (the *stored authorisation* — not login OAuth).
  * connectors/kb/     KB connector CRUD (the *configuration row*; the
                       provider engines live in ``core/kb_connectors/``).
  * llm/               LLM provider factory + credentials store.
  * mcp/               Model Context Protocol server connections.

Rule of thumb: if it's "we hit an outside service" (or vice-versa),
it lives here. Identity providers (Google/GitHub login, SSO) belong
in ``identity/auth/`` instead — they're authentication, not data.
"""
