"use client";

import { useState } from "react";
import { Lock } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { MonacoEditor } from "../MonacoEditor";

type DbType = "postgresql" | "mysql" | "sqlite";

interface DbConnectionFields {
  db_type: DbType;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
}

interface DbConfig {
  connection_string: string;
  query_template: string;
  max_rows: number;
  _fields?: DbConnectionFields;
}

const DEFAULT_PORTS: Record<DbType, string> = {
  postgresql: "5432",
  mysql: "3306",
  sqlite: "",
};

function buildConnectionString(fields: DbConnectionFields): string {
  const { db_type, host, port, database, username, password, ssl } = fields;
  if (db_type === "sqlite") {
    return `sqlite:///${database}`;
  }
  const scheme = db_type === "mysql" ? "mysql" : "postgresql";
  const auth = username ? `${encodeURIComponent(username)}:${encodeURIComponent(password)}@` : "";
  const portPart = port ? `:${port}` : "";
  const sslParam = ssl && db_type === "postgresql" ? "?sslmode=require" : "";
  return `${scheme}://${auth}${host}${portPart}/${database}${sslParam}`;
}

function fieldsFromConnectionString(cs: string, dbType: DbType): DbConnectionFields {
  try {
    const url = new URL(cs);
    return {
      db_type: dbType,
      host: url.hostname,
      port: url.port || DEFAULT_PORTS[dbType],
      database: url.pathname.slice(1),
      username: decodeURIComponent(url.username),
      password: decodeURIComponent(url.password),
      ssl: url.searchParams.get("sslmode") === "require",
    };
  } catch {
    return {
      db_type: dbType,
      host: "localhost",
      port: DEFAULT_PORTS[dbType],
      database: "",
      username: "",
      password: "",
      ssl: false,
    };
  }
}

function parseConfig(raw: Record<string, unknown>): DbConfig & { _fields: DbConnectionFields } {
  const cs = (raw.connection_string as string) ?? "";
  const dbType: DbType =
    cs.startsWith("postgresql") ? "postgresql"
    : cs.startsWith("mysql") ? "mysql"
    : cs.startsWith("sqlite") ? "sqlite"
    : "postgresql";

  const savedFields = raw._fields as DbConnectionFields | undefined;
  const fields = savedFields ?? fieldsFromConnectionString(cs, dbType);

  return {
    connection_string: cs,
    query_template: (raw.query_template as string) ?? "SELECT * FROM {table_name} LIMIT {limit};",
    max_rows: typeof raw.max_rows === "number" ? raw.max_rows : 50,
    _fields: { ...fields, db_type: dbType },
  };
}

interface DbConfigFormProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export function DbConfigForm({ value, onChange }: DbConfigFormProps) {
  const cfg = parseConfig(value);
  const [fields, setFields] = useState<DbConnectionFields>(cfg._fields);

  const updateFields = (patch: Partial<DbConnectionFields>) => {
    const updated = { ...fields, ...patch };
    // Reset port when DB type changes
    if (patch.db_type && patch.db_type !== fields.db_type) {
      updated.port = DEFAULT_PORTS[patch.db_type];
    }
    setFields(updated);
    onChange({
      ...cfg,
      connection_string: buildConnectionString(updated),
      _fields: updated,
    });
  };

  const updateCfg = (patch: Partial<Omit<DbConfig, "_fields">>) => {
    onChange({ ...cfg, ...patch, _fields: fields });
  };

  return (
    <div className="space-y-5">
      <div className="space-y-3 rounded-lg border border-border/60 bg-muted/30 p-4">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Connection
        </h3>

        {/* DB Type */}
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">Database type</Label>
          <Select
            value={fields.db_type}
            onValueChange={(v) => updateFields({ db_type: v as DbType })}
          >
            <SelectTrigger className="h-8 w-44 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="postgresql" className="text-xs">PostgreSQL</SelectItem>
              <SelectItem value="mysql" className="text-xs">MySQL / MariaDB</SelectItem>
              <SelectItem value="sqlite" className="text-xs">SQLite (file path)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {fields.db_type === "sqlite" ? (
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Database file path</Label>
            <Input
              className="h-8 font-mono text-xs"
              placeholder="/data/database.db"
              value={fields.database}
              onChange={(e) => updateFields({ database: e.target.value })}
            />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-[1fr_100px] gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Host</Label>
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder="localhost or {db_host}"
                  value={fields.host}
                  onChange={(e) => updateFields({ host: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Port</Label>
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder={DEFAULT_PORTS[fields.db_type]}
                  value={fields.port}
                  onChange={(e) => updateFields({ port: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Database name</Label>
              <Input
                className="h-8 font-mono text-xs"
                placeholder="myapp_db"
                value={fields.database}
                onChange={(e) => updateFields({ database: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Username</Label>
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder="{db_user}"
                  value={fields.username}
                  onChange={(e) => updateFields({ username: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    type="password"
                    className="h-8 pl-8 font-mono text-xs"
                    placeholder="{db_password}"
                    value={fields.password}
                    onChange={(e) => updateFields({ password: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Switch
                checked={fields.ssl}
                onCheckedChange={(v) => updateFields({ ssl: v })}
              />
              <Label className="text-xs cursor-pointer">Require SSL / TLS</Label>
            </div>
          </>
        )}

        {/* Connection string preview */}
        <div className="rounded border border-border/60 bg-background p-2">
          <p className="mb-1 text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
            Connection string preview
          </p>
          <code className="break-all text-[11px] text-foreground">
            {buildConnectionString(fields) || "—"}
          </code>
        </div>
      </div>

      {/* Query template */}
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">SQL Query Template</Label>
        <p className="text-[11px] text-muted-foreground">
          Use <code className="rounded bg-muted px-1">{"{variable}"}</code> for dynamic values.
          Queries run read-only.
        </p>
        <MonacoEditor
          language="sql"
          height={200}
          value={cfg.query_template}
          onChange={(v) => updateCfg({ query_template: v })}
        />
      </div>

      {/* Max rows */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground">Max rows returned</Label>
          <span className="font-mono text-xs font-medium">{cfg.max_rows}</span>
        </div>
        <Slider
          min={1}
          max={1000}
          step={10}
          value={[cfg.max_rows]}
          onValueChange={([v]) => updateCfg({ max_rows: v })}
        />
      </div>
    </div>
  );
}
