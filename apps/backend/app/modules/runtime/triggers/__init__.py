"""runtime/triggers/ — what makes a workflow run start.

Two flavours, picked up by the upcoming base abstraction:

  WebhookTrigger    HTTP-driven. The platform exposes a route the
                    provider hits with a payload (signed). We verify
                    the signature, parse the payload, dispatch the
                    workflow.
                      slack/  teams/  discord/  http/

  PollingTrigger    Pull-driven. A background loop ticks every N
                    seconds, checks an external source for new events
                    since the last cursor, dispatches per event.
                      scheduled/  email/

Adding a new trigger type:
  1. Create the sub-folder (router.py + service.py).
  2. Inherit WebhookTrigger or PollingTrigger from ``_base.py``
     (built in the follow-up commit) — surfaces the per-provider
     signing in ``_signing.py`` and the workflow-dispatch util as
     shared base behaviour.
  3. Wire the router in main.py.
"""
