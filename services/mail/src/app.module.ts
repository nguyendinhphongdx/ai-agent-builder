import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import configs from './config/index.js';
import { MailProviderModule } from './providers/mail-provider.module.js';
import { TemplateService } from './templates/template.service.js';
import { MailService } from './mail/mail.service.js';
import { MailController } from './mail/mail.controller.js';
import { HealthController } from './health/health.controller.js';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: configs,
      envFilePath: ['.env.local', '.env'],
    }),
    MailProviderModule,
  ],
  controllers: [HealthController, MailController],
  providers: [TemplateService, MailService],
})
export class AppModule {}
