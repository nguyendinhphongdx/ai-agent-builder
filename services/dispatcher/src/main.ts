import { NestFactory } from '@nestjs/core';
import { Logger } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const logger = new Logger('Dispatcher');
  const app = await NestFactory.create(AppModule);

  // Enable shutdown hooks
  app.enableShutdownHooks();

  // Get port from environment
  const port = process.env.PORT || 3010;

  // Start HTTP server for health checks
  await app.listen(port);

  logger.log(`AgentForge dispatcher started on port ${port}`);
  logger.log(`Health: http://localhost:${port}/health`);
}

bootstrap().catch((error) => {
  console.error('Failed to start dispatcher:', error);
  process.exit(1);
});
