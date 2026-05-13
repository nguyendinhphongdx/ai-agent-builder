import { AtSign } from "lucide-react";
import { EmailRow } from "./email-row";
import { EmailForm } from "./email-form";
import type { TriggerProvider } from "./types";

export const emailProvider: TriggerProvider = {
  type: "email",
  label: "Email (IMAP)",
  icon: AtSign,
  cardTitle: "Email triggers",
  cardDescription:
    "One IMAP mailbox per trigger. New messages enqueue a workflow run.",
  emptyMessage: "No email triggers yet.",
  RowComponent: EmailRow,
  FormComponent: EmailForm,
};
