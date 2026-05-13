import type { TriggerProvider } from "./types";
import { emailProvider } from "./email";
import { slackProvider } from "./slack";
import { teamsProvider } from "./teams";
import { discordProvider } from "./discord";

/**
 * Ordered list of inbound trigger providers shown in the Triggers page.
 * Adding a fifth provider:
 *   1. New file `providers/<name>.ts` exporting a `TriggerProvider`
 *      constant (plus the Row + Form components, conventionally in
 *      `<name>-row.tsx` and `<name>-form.tsx`).
 *   2. Append it here.
 * No changes to TriggersView itself.
 */
export const TRIGGER_PROVIDERS: TriggerProvider[] = [
  emailProvider,
  slackProvider,
  teamsProvider,
  discordProvider,
];

export type { TriggerProvider } from "./types";
