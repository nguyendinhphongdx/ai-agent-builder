import { NestFactory } from '@nestjs/core';
import { Logger } from '@nestjs/common';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const logger = new Logger('MailService');
  const app = await NestFactory.create(AppModule);

  // CORS - production không cần vì chỉ nhận request từ internal services
  if (process.env.NODE_ENV !== 'production') {
    app.enableCors({ origin: '*' });
  }

  app.enableShutdownHooks();

  const port = process.env.PORT || 3011;
  await app.listen(port);

  logger.log(`Mail service started on port ${port}`);
}

bootstrap();
