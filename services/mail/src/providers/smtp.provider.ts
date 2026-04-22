import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import nodemailer, { type Transporter } from 'nodemailer';
import type { MailProvider, SendMailOptions, MailResult } from './mail-provider.interface.js';

@Injectable()
export class SmtpProvider implements MailProvider {
  private readonly logger = new Logger(SmtpProvider.name);
  private readonly transporter: Transporter;
  private readonly fromEmail: string;
  private readonly fromName: string;

  constructor(private readonly configService: ConfigService) {
    const host = this.configService.get<string>('SMTP_HOST');
    const port = parseInt(this.configService.get<string>('SMTP_PORT', '587'), 10);
    const secure = this.configService.get<string>('SMTP_SECURE', 'false') === 'true';
    const user = this.configService.get<string>('SMTP_USER');
    const pass = this.configService.get<string>('SMTP_PASS');

    this.fromEmail = this.configService.get<string>('MAIL_FROM', 'noreply@agentforge.com');
    this.fromName = this.configService.get<string>('MAIL_FROM_NAME', 'AgentForge');

    if (!host) {
      this.logger.error('SMTP_HOST is not configured - emails will fail');
    }

    this.transporter = nodemailer.createTransport({
      host,
      port,
      secure,
      auth: user && pass ? { user, pass } : undefined,
    });

    this.logger.log(`SMTP configured: ${host}:${port} (secure=${secure}, auth=${user ? 'yes' : 'no'})`);
    this.logger.log(`Mail from: ${this.fromName} <${this.fromEmail}>`);
  }

  async send(options: SendMailOptions): Promise<MailResult> {
    try {
      const recipients = Array.isArray(options.to) ? options.to : [options.to];

      const info = await this.transporter.sendMail({
        to: recipients,
        from: {
          address: options.from || this.fromEmail,
          name: this.fromName,
        },
        subject: options.subject,
        text: options.text,
        html: options.html,
        replyTo: options.replyTo,
        attachments: options.attachments?.map((att) => ({
          filename: att.filename,
          content: att.content,
          path: att.path,
          contentType: att.contentType,
        })),
      });

      this.logger.log(`Email sent to ${recipients.join(', ')} (messageId=${info.messageId})`);

      return {
        success: true,
        messageId: info.messageId,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Failed to send email: ${errorMessage}`);

      return {
        success: false,
        error: errorMessage,
      };
    }
  }
}
