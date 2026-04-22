import { Controller, Get } from '@nestjs/common';
import { MailService } from '../mail/mail.service.js';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  uptime: number;
  templates: string[];
}

@Controller()
export class HealthController {
  private readonly startTime = Date.now();

  constructor(private readonly mailService: MailService) {}

  @Get('health')
  getHealth(): HealthResponse {
    return {
      status: 'ok',
      service: 'mail-service',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      templates: this.mailService.getAvailableTemplates(),
    };
  }

  @Get('healthz')
  getLiveness(): { status: string } {
    return { status: 'ok' };
  }

  @Get('readyz')
  getReadiness(): { status: string } {
    return { status: 'ok' };
  }
}
