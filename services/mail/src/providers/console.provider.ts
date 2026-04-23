import { Injectable, Logger } from '@nestjs/common';
import type { MailProvider, SendMailOptions, MailResult } from './mail-provider.interface.js';

@Injectable()
export class ConsoleProvider implements MailProvider {
  private readonly logger = new Logger(ConsoleProvider.name);

  async send(options: SendMailOptions): Promise<MailResult> {
    const recipients = Array.isArray(options.to) ? options.to.join(', ') : options.to;
    const messageId = `console-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const lines: string[] = [
      '',
      '═══════════════════ MAIL (console driver) ═══════════════════',
      `MessageId: ${messageId}`,
      `To:        ${recipients}`,
      `From:      ${options.from ?? '(default from config)'}`,
      `ReplyTo:   ${options.replyTo ?? '(none)'}`,
      `Subject:   ${options.subject}`,
    ];

    if (options.text) {
      lines.push('', '── Text body ──', options.text);
    }

    if (options.html) {
      const textPreview = this.htmlToText(options.html);
      lines.push(
        '',
        `── HTML preview (${options.html.length} chars, tags stripped) ──`,
        textPreview,
      );
    }

    if (options.attachments?.length) {
      lines.push('', `Attachments: ${options.attachments.map((a) => a.filename).join(', ')}`);
    }

    lines.push('══════════════════════════════════════════════════════════════', '');

    // Single log call → all lines stay together in output (no interleaving with other logs)
    this.logger.log(lines.join('\n'));

    return {
      success: true,
      messageId,
    };
  }

  /**
   * Strip HTML tags and decode common entities — keeps the email readable in
   * terminal without flooding it with markup. Not a real HTML parser, just
   * good enough for dev preview.
   */
  private htmlToText(html: string): string {
    const stripped = html
      .replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '')        // drop <head> entirely (title/meta/MSO)
      .replace(/<!--[\s\S]*?-->/g, '')                      // HTML comments + IE conditionals
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|div|h[1-6]|li|tr|td)>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'");

    // Trim each line + collapse consecutive blank lines to max 1
    return stripped
      .split('\n')
      .map((line) => line.replace(/\s+/g, ' ').trim())
      .filter((line, i, arr) => line || (i > 0 && arr[i - 1]))
      .join('\n')
      .trim();
  }
}
