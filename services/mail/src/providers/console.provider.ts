import { Injectable, Logger } from '@nestjs/common';
import type { MailProvider, SendMailOptions, MailResult } from './mail-provider.interface.js';

@Injectable()
export class ConsoleProvider implements MailProvider {
  private readonly logger = new Logger(ConsoleProvider.name);

  async send(options: SendMailOptions): Promise<MailResult> {
    const recipients = Array.isArray(options.to) ? options.to.join(', ') : options.to;
    const messageId = `console-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    this.logger.log('─────────── MAIL (console driver) ───────────');
    this.logger.log(`MessageId: ${messageId}`);
    this.logger.log(`To:        ${recipients}`);
    this.logger.log(`From:      ${options.from ?? '(default from config)'}`);
    this.logger.log(`ReplyTo:   ${options.replyTo ?? '(none)'}`);
    this.logger.log(`Subject:   ${options.subject}`);
    if (options.text) {
      const preview = options.text.slice(0, 200);
      this.logger.log(`Text:      ${preview}${options.text.length > 200 ? '...' : ''}`);
    }
    if (options.html) {
      this.logger.log(`HTML:      ${options.html.length} chars — ${options.html.slice(0, 150)}...`);
    }
    if (options.attachments?.length) {
      this.logger.log(`Attachments: ${options.attachments.map((a) => a.filename).join(', ')}`);
    }
    this.logger.log('──────────────────────────────────────────────');

    return {
      success: true,
      messageId,
    };
  }
}
