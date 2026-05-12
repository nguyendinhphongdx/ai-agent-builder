"""Plugin manifest schema + YAML loader.

Manifest contract (plugin.yaml):

    id: my-jira-tool                # globally unique slug
    version: 1.0.0                  # semver
    name: Jira Tool                 # display name
    description: Create Jira issues # one-line summary
    runtime: python                 # python | nodejs | docker
    entrypoint: main.py             # runtime-specific
    capabilities:                   # what the plugin contributes
      - tool                        # tool | trigger | extractor | …
    permissions:                    # plugin daemon enforces these
      http_outbound: ["jira.com"]   # allowed host whitelist
      secrets: ["JIRA_API_KEY"]     # secrets the plugin may read
    tools:                          # only if "tool" in capabilities
      - name: create_issue
        description: Create a Jira issue.
        input_schema: {...}         # JSON Schema for params
        output_schema: {...}

Validation rules:
  - id must be lowercase-kebab + non-empty
  - version must look like semver
  - runtime must be one of the three known values
  - tool entries are validated only when "tool" in capabilities
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Allow letters, digits, hyphens. Conservative — avoids issues
# with URL slugs and filesystem paths.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][\w.\-]+)?$")

RUNTIMES = ("python", "nodejs", "docker")
CAPABILITIES = ("tool", "trigger", "extractor", "exporter")


class ToolEntry(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class Permissions(BaseModel):
    http_outbound: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)


class PluginManifest(BaseModel):
    id: str
    version: str
    name: str
    description: str | None = None
    runtime: str
    entrypoint: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: Permissions = Field(default_factory=Permissions)
    tools: list[ToolEntry] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError(
                "id must be lowercase letters/digits/hyphens, "
                "starting with a letter, max 64 chars"
            )
        return v

    @field_validator("version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(f"version must be semver, got {v!r}")
        return v

    @field_validator("runtime")
    @classmethod
    def _check_runtime(cls, v: str) -> str:
        if v not in RUNTIMES:
            raise ValueError(f"runtime must be one of {RUNTIMES}, got {v!r}")
        return v

    @field_validator("capabilities")
    @classmethod
    def _check_capabilities(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if c not in CAPABILITIES]
        if bad:
            raise ValueError(
                f"unknown capabilities: {bad}. Allowed: {CAPABILITIES}"
            )
        return v


def parse_manifest(raw: str | dict[str, Any]) -> PluginManifest:
    """Parse + validate a plugin manifest.

    Accepts either a YAML string or an already-parsed dict (caller
    might have read from a remote source as JSON). Raises
    ``ValueError`` on invalid input.
    """
    if isinstance(raw, str):
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to parse plugin manifests; pip install pyyaml"
            ) from exc
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError(f"plugin.yaml is not valid YAML: {exc}") from exc
    else:
        data = raw
    if not isinstance(data, dict):
        raise ValueError("plugin manifest must be a mapping at the top level")
    return PluginManifest.model_validate(data)
