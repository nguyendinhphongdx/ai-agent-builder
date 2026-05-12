"""integrations/connectors/ — stored external-system links.

  * oauth/  3-legged OAuth connections (one row per workspace-Slack /
            workspace-Notion / workspace-Dropbox pair). Tokens stored
            Fernet-encrypted, refreshed transparently.
  * kb/     CRUD for KB connector rows (which provider, which config,
            which OAuth connection). The actual fetch/sync engines
            live in ``core/kb_connectors/providers/``.

Adding a new connector type: define the row schema + provider engine
in core, then surface it here with a thin router.
"""
