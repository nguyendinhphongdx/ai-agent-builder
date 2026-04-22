import { Injectable, Inject, Logger } from '@nestjs/common';
import {
  MAIL_PROVIDER,
  type MailProvider,
  type MailResult,
  type SendMailOptions,
} from '../providers/mail-provider.interface.js';
import { TemplateService } from '../templates/template.service.js';
import type { MailMessage } from './mail.types.js';

@Injectable()
export class MailService {
  private readonly logger = new Logger(MailService.name);

  constructor(
    @Inject(MAIL_PROVIDER) private readonly mailProvider: MailProvider,
    private readonly templateService: TemplateService,
  ) {}

  async send(message: MailMessage): Promise<MailResult> {
    try {
      let html = message.html;
      let text = message.text;

      // Render template if specified
      if (message.template) {
        if (!this.templateService.hasTemplate(message.template)) {
          return {
            success: false,
            error: `Template not found: ${message.template}`,
          };
        }

        html = this.templateService.render(message.template, message.data || {});
      }

      // Ensure we have content
      if (!html && !text) {
        return {
          success: false,
          error: 'Email must have either html or text content',
        };
      }

      const options: SendMailOptions = {
        to: message.to,
        subject: message.subject,
        html,
        text,
        from: message.from,
        replyTo: message.replyTo,
        attachments: message.attachments,
      };

      return await this.mailProvider.send(options);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Failed to send email: ${errorMessage}`);

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async sendDirect(options: SendMailOptions): Promise<MailResult> {
    return this.mailProvider.send(options);
  }

  getAvailableTemplates(): string[] {
    return this.templateService.getAvailableTemplates();
  }
}
