import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import sgMail, { type MailDataRequired } from '@sendgrid/mail';
import type { MailProvider, SendMailOptions, MailResult } from './mail-provider.interface.js';

@Injectable()
export class SendGridProvider implements MailProvider {
  private readonly logger = new Logger(SendGridProvider.name);
  private readonly fromEmail: string;
  private readonly fromName: string;

  constructor(private readonly configService: ConfigService) {
    const apiKey = this.configService.get<string>('SENDGRID_API_KEY');
    this.fromEmail = this.configService.get<string>('MAIL_FROM', 'noreply@agentforge.com');
    this.fromName = this.configService.get<string>('MAIL_FROM_NAME', 'AgentForge');

    // Log configuration status on startup
    if (!apiKey) {
      this.logger.error('SENDGRID_API_KEY is not configured - emails will fail');
    } else {
      sgMail.setApiKey(apiKey);
      this.logger.log('SendGrid configured successfully');
    }

    this.logger.log(`Mail from: ${this.fromName} <${this.fromEmail}>`);
  }

  async send(options: SendMailOptions): Promise<MailResult> {
    try {
      const recipients = Array.isArray(options.to) ? options.to : [options.to];

      const msg: MailDataRequired = {
        to: recipients,
        from: {
          email: options.from || this.fromEmail,
          name: this.fromName,
        },
        subject: options.subject,
        text: options.text || ' ',
        html: options.html,
        replyTo: options.replyTo,
        attachments: options.attachments
          ?.filter((att) => att.content)
          .map((att) => ({
            filename: att.filename,
            content:
              typeof att.content === 'string'
                ? att.content
                : att.content!.toString('base64'),
            type: att.contentType,
            disposition: 'attachment' as const,
          })),
      };

      const [response] = await sgMail.send(msg);

      this.logger.log(`Email sent successfully to ${recipients.join(', ')}`);

      return {
        success: true,
        messageId: response.headers['x-message-id'] as string,
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
