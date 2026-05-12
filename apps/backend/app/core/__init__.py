"""Heavy engines — provider-agnostic primitives reused by feature
modules. Lives outside the feature folders because (a) ownership
is cross-cutting and (b) the modules here are big enough that
folding them into a single feature would make that folder dwarf
the rest of the codebase.

What lives here:
  * workflow_runner — graph execution engine (used by workflows,
    webhooks, internal HTTP, sub_workflow node)
  * retrieval       — KB query engine (used by knowledge.router +
    the agents executor)
  * ingestion       — file → chunks → embeddings pipeline
  * kb_connectors   — 10 provider implementations + base + sync
                      orchestration

What does NOT belong here:
  * HTTP routers / schemas    — those stay with their feature
  * SQLAlchemy models         — see app/models/
  * Schedulers / async loops  — see app/background/
"""
