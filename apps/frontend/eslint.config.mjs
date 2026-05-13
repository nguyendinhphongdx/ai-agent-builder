import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

/**
 * Feature folders under `src/features/`. Each gets a generated config
 * block that forbids importing from *other* features — encouraging
 * either a public barrel (`features/X/index.ts`) or promotion of
 * shared code up to `components/`, `hooks/`, or `lib/`.
 *
 * Starts as a *warning* so existing violations (e.g.
 * WorkflowSettingsView → TriggersView deep import) don't break the
 * build; tighten to error once features publish stable barrels.
 */
const FEATURES = [
  "admin",
  "agents",
  "annotations",
  "auth",
  "billing",
  "chat",
  "connections",
  "dashboard",
  "hub",
  "integrations",
  "jobs",
  "knowledge",
  "landing",
  "notifications",
  "onboarding",
  "settings",
  "tools",
  "triggers",
  "usage",
  "workflows",
  "workspaces",
];

const featureBoundaryConfigs = FEATURES.map((feature) => ({
  files: [`src/features/${feature}/**/*.{ts,tsx}`],
  rules: {
    "no-restricted-imports": [
      "warn",
      {
        patterns: [
          {
            group: [
              "@/features/*/**",
              `!@/features/${feature}/**`,
            ],
            message:
              "Cross-feature deep imports are discouraged. Either import via the target feature's index barrel, or promote shared code to components/, hooks/, or lib/.",
          },
        ],
      },
    ],
  },
}));

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  ...featureBoundaryConfigs,
]);

export default eslintConfig;
