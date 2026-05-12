"""runtime/ — HOW things activate and talk back.

  * chat/           — user-facing conversations (auth, public share, ratings)
  * triggers/       — what starts a workflow run (cron, slack, http, …)
  * jobs/           — background queue producer + idempotency
  * notifications/  — push events + persistent inbox
  * uploads/        — request-time file upload endpoints

If a feature is "fired by an event" or "shows up in the user's
chat / bell / inbox", it belongs here.
"""
