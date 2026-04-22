import { Module, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { MAIL_PROVIDER, type MailProvider } from './mail-provider.interface.js';
import { SendGridProvider } from './sendgrid.provider.js';
import { SmtpProvider } from './smtp.provider.js';
import { ConsoleProvider } from './console.provider.js';

const SUPPORTED_DRIVERS = ['sendgrid', 'smtp', 'console'] as const;
type MailDriver = (typeof SUPPORTED_DRIVERS)[number];

function createProvider(driver: MailDriver, config: ConfigService): MailProvider {
  switch (driver) {
    case 'sendgrid':
      return new SendGridProvider(config);
    case 'smtp':
      return new SmtpProvider(config);
    case 'console':
      return new ConsoleProvider();
  }
}

@Module({
  providers: [
    {
      provide: MAIL_PROVIDER,
      useFactory: (config: ConfigService): MailProvider => {
        const logger = new Logger('MailProviderModule');
        const driver = config.get<string>('MAIL_DRIVER', 'sendgrid').toLowerCase();

        if (!SUPPORTED_DRIVERS.includes(driver as MailDriver)) {
          throw new Error(
            `Unknown MAIL_DRIVER: "${driver}". Supported: ${SUPPORTED_DRIVERS.join(', ')}`,
          );
        }

        logger.log(`Using mail driver: ${driver}`);
        return createProvider(driver as MailDriver, config);
      },
      inject: [ConfigService],
    },
  ],
  exports: [MAIL_PROVIDER],
})
export class MailProviderModule {}
