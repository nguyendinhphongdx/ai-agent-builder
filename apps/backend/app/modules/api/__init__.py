"""api/ — audience layers (axis perpendicular to features).

  * external/  public API — embedded chat widget, programmatic clients
               using personal access tokens or API keys.
  * internal/  routes only the jobs runner hits (X-Job-Token guard).
               Internal endpoints cross-cut multiple features (KB
               ingest, workflow run, …) and historically lived here
               because the *audience* is what's special, not the
               feature.
  * admin/     admin-only routes (instance admins, not workspace admins).

These are *audience routes*, not features — they exist because a
single feature can have routes for multiple audiences (auth users,
job runner, admins). When a feature gets enough audience-specific
routes to warrant moving them into the feature folder, do so and
shrink these.
"""
