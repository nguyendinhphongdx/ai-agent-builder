import type { Attachment } from '../providers/mail-provider.interface.js';

export interface MailMessage {
  to: string | string[];
  subject: string;
  template?: string;
  data?: Record<string, unknown>;
  html?: string;
  text?: string;
  attachments?: Attachment[];
  from?: string;
  replyTo?: string;
  priority?: 'high' | 'normal' | 'low';
}
