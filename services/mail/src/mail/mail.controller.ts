import { Controller, Post, Body, Get, HttpCode, HttpStatus } from '@nestjs/common';
import { MailService } from './mail.service.js';
import type { MailMessage } from './mail.types.js';
import type { MailResult } from '../providers/mail-provider.interface.js';

@Controller('mail')
export class MailController {
  constructor(private readonly mailService: MailService) {}

  @Post('send')
  @HttpCode(HttpStatus.OK)
  async send(@Body() message: MailMessage): Promise<MailResult> {
    return this.mailService.send(message);
  }

  @Get('templates')
  getTemplates(): { templates: string[] } {
    return {
      templates: this.mailService.getAvailableTemplates(),
    };
  }
}
