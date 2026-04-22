export interface Attachment {
  filename: string;
  content?: string | Buffer;
  path?: string;
  contentType?: string;
}

export interface SendMailOptions {
  to: string | string[];
  subject: string;
  text?: string;
  html?: string;
  attachments?: Attachment[];
  from?: string;
  replyTo?: string;
}

export interface MailResult {
  success: boolean;
  messageId?: string;
  error?: string;
}

export interface MailProvider {
  send(options: SendMailOptions): Promise<MailResult>;
}

export const MAIL_PROVIDER = 'MAIL_PROVIDER';
