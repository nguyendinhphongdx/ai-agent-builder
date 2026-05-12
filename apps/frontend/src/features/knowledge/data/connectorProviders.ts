/**
 * Connector provider catalog — one canonical source for the
 * picker + the dynamic form. Mirrors the backend registry in
 * apps/backend/app/knowledge/connectors/__init__.py.
 *
 * Field types:
 *   text       single-line input
 *   password   single-line, masked (credentials)
 *   textarea   multi-line (e.g. service account JSON, URL list)
 *   number     numeric input with min/max
 *   boolean    checkbox
 *
 * Adding a new provider here surfaces it in the FE picker without
 * touching every view — the backend just needs the matching
 * registry entry.
 */

export type ConnectorFieldType =
  | "text"
  | "password"
  | "textarea"
  | "number"
  | "boolean";

export interface ConnectorField {
  key: string;
  label: string;
  type: ConnectorFieldType;
  placeholder?: string;
  help?: string;
  required?: boolean;
  default?: string | number | boolean;
}

export interface ConnectorProvider {
  id: string;
  label: string;
  description: string;
  /** Lucide icon name to render in the picker. */
  icon: string;
  /** Auth flavour — surfaced as a chip in the picker. */
  authStyle: "none" | "api-key" | "oauth-token" | "sa-json" | "app-only";
  configFields: ConnectorField[];
  credentialFields: ConnectorField[];
}

export const CONNECTOR_PROVIDERS: ConnectorProvider[] = [
  {
    id: "local_fs",
    label: "Local filesystem",
    description: "Index a folder on the backend host. Dev / on-prem only.",
    icon: "FolderOpen",
    authStyle: "none",
    configFields: [
      {
        key: "root",
        label: "Root directory",
        type: "text",
        placeholder: "/var/data/docs",
        required: true,
      },
      {
        key: "recursive",
        label: "Recursive",
        type: "boolean",
        default: true,
      },
    ],
    credentialFields: [],
  },
  {
    id: "s3",
    label: "AWS S3 / S3-compatible",
    description: "S3, MinIO, R2, Wasabi, DigitalOcean Spaces.",
    icon: "Cloud",
    authStyle: "api-key",
    configFields: [
      { key: "bucket", label: "Bucket", type: "text", required: true },
      { key: "prefix", label: "Prefix", type: "text", placeholder: "documents/" },
      {
        key: "region",
        label: "Region",
        type: "text",
        placeholder: "us-east-1",
      },
      {
        key: "endpoint_url",
        label: "Endpoint URL",
        type: "text",
        placeholder: "https://s3.amazonaws.com (leave blank for AWS)",
        help: "Set this for MinIO / R2 / Wasabi / DigitalOcean Spaces.",
      },
    ],
    credentialFields: [
      {
        key: "access_key_id",
        label: "Access key id",
        type: "text",
        help: "Leave blank to use the backend's IAM role / env credentials.",
      },
      {
        key: "secret_access_key",
        label: "Secret access key",
        type: "password",
      },
      {
        key: "session_token",
        label: "Session token (STS)",
        type: "password",
      },
    ],
  },
  {
    id: "web",
    label: "Web URL crawler",
    description: "Index public URLs or a sitemap.xml.",
    icon: "Globe",
    authStyle: "none",
    configFields: [
      {
        key: "sitemap",
        label: "Sitemap URL",
        type: "text",
        placeholder: "https://example.com/sitemap.xml",
        help: "Walk the sitemap and incremental-sync via <lastmod>.",
      },
      {
        key: "urls",
        label: "Explicit URL list (one per line)",
        type: "textarea",
        placeholder: "https://docs.example.com/page-1\nhttps://docs.example.com/page-2",
        help: "Use when there's no sitemap. Comma- or newline-separated.",
      },
      {
        key: "max_urls",
        label: "Max URLs per tick",
        type: "number",
        default: 200,
      },
    ],
    credentialFields: [],
  },
  {
    id: "notion",
    label: "Notion",
    description: "Pages + databases via integration token.",
    icon: "FileText",
    authStyle: "oauth-token",
    configFields: [
      {
        key: "database_id",
        label: "Database id (optional)",
        type: "text",
        placeholder: "Notion database id",
      },
      {
        key: "search_query",
        label: "Search query (optional)",
        type: "text",
        help: "Filter pages by a search term. Leave blank for all accessible pages.",
      },
    ],
    credentialFields: [
      {
        key: "integration_token",
        label: "Integration token",
        type: "password",
        required: true,
        help: "Create at notion.so/my-integrations. Share the workspace / database with the integration first.",
      },
    ],
  },
  {
    id: "gcs",
    label: "Google Cloud Storage",
    description: "GCS buckets via service account.",
    icon: "Cloud",
    authStyle: "sa-json",
    configFields: [
      { key: "bucket", label: "Bucket", type: "text", required: true },
      { key: "prefix", label: "Prefix", type: "text" },
    ],
    credentialFields: [
      {
        key: "service_account_json",
        label: "Service account JSON",
        type: "textarea",
        help: "Paste the SA key JSON. Needs storage.objectViewer at minimum.",
      },
    ],
  },
  {
    id: "azure_blob",
    label: "Azure Blob Storage",
    description: "Azure Blob via connection string or SAS / key.",
    icon: "Cloud",
    authStyle: "api-key",
    configFields: [
      { key: "container", label: "Container", type: "text", required: true },
      { key: "account_name", label: "Account name", type: "text" },
      { key: "prefix", label: "Prefix", type: "text" },
      {
        key: "endpoint_suffix",
        label: "Endpoint suffix",
        type: "text",
        default: "core.windows.net",
        help: "Override for sovereign clouds (e.g. core.usgovcloudapi.net).",
      },
    ],
    credentialFields: [
      {
        key: "connection_string",
        label: "Connection string",
        type: "password",
        help: "Preferred — wraps account name + key + endpoint into one secret.",
      },
      {
        key: "account_key",
        label: "Account key",
        type: "password",
      },
      {
        key: "sas_token",
        label: "SAS token",
        type: "password",
      },
    ],
  },
  {
    id: "gdrive",
    label: "Google Drive",
    description: "Drive folder / shared drive via service account.",
    icon: "FolderOpen",
    authStyle: "sa-json",
    configFields: [
      {
        key: "folder_id",
        label: "Folder id (optional)",
        type: "text",
        help: "Restrict to one folder. Share it with the service account email.",
      },
      {
        key: "shared_drive_id",
        label: "Shared drive id (optional)",
        type: "text",
      },
    ],
    credentialFields: [
      {
        key: "service_account_json",
        label: "Service account JSON",
        type: "textarea",
        required: true,
        help: "SA must have drive.readonly scope. Share the target folder with the SA email.",
      },
    ],
  },
  {
    id: "confluence",
    label: "Confluence",
    description: "Atlassian Cloud pages via email + API token.",
    icon: "FileText",
    authStyle: "api-key",
    configFields: [
      {
        key: "base_url",
        label: "Base URL",
        type: "text",
        placeholder: "https://your-org.atlassian.net",
        required: true,
      },
      {
        key: "space_key",
        label: "Space key (optional)",
        type: "text",
        help: "Restrict to one space.",
      },
      {
        key: "include_blogposts",
        label: "Include blog posts",
        type: "boolean",
        default: false,
      },
    ],
    credentialFields: [
      { key: "email", label: "Atlassian email", type: "text", required: true },
      {
        key: "api_token",
        label: "API token",
        type: "password",
        required: true,
        help: "Mint at id.atlassian.com/manage-profile/security/api-tokens.",
      },
    ],
  },
  {
    id: "msgraph",
    label: "SharePoint / OneDrive",
    description: "Microsoft 365 via Graph delta API (app-only).",
    icon: "Cloud",
    authStyle: "app-only",
    configFields: [
      {
        key: "drive_id",
        label: "Drive id",
        type: "text",
        required: true,
        help: "Find via /sites/{site}/drives or /users/{user}/drive.",
      },
    ],
    credentialFields: [
      { key: "tenant_id", label: "Tenant id", type: "text", required: true },
      { key: "client_id", label: "Client id", type: "text", required: true },
      {
        key: "client_secret",
        label: "Client secret",
        type: "password",
        required: true,
        help: "App permissions needed: Sites.Read.All + Files.Read.All.",
      },
    ],
  },
  {
    id: "dropbox",
    label: "Dropbox",
    description: "Dropbox files via long-lived access token.",
    icon: "FolderOpen",
    authStyle: "oauth-token",
    configFields: [
      {
        key: "path",
        label: "Path",
        type: "text",
        placeholder: "/folder or leave blank for root",
      },
      { key: "recursive", label: "Recursive", type: "boolean", default: true },
    ],
    credentialFields: [
      {
        key: "access_token",
        label: "Access token",
        type: "password",
        required: true,
        help: "Generate at dropbox.com/developers/apps with files.metadata.read + files.content.read scopes.",
      },
    ],
  },
];

export function findProvider(id: string): ConnectorProvider | undefined {
  return CONNECTOR_PROVIDERS.find((p) => p.id === id);
}
