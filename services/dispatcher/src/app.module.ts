import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';
import { ServiceRegistry } from './config/service-registry';
import { DispatcherConsumer } from './consumer/dispatcher.consumer';
import { HttpClientService } from './services/http-client.service';
import { HealthController } from './health/health.controller';
import { DispatchController, DispatchService } from './dispatch';
import { DispatcherAuthGuard } from './auth';

// Main exchange — routes dispatches to per-workload queues
const DISPATCHER_EXCHANGE = {
  name: 'dispatcher',
  type: 'topic' as const,
  options: { durable: true },
};

// Retry exchange — holds delayed messages; dead-letters back to main exchange
// with original routing key preserved (so message goes back to its original queue).
const DISPATCHER_RETRY_EXCHANGE = {
  name: 'dispatcher.retry',
  type: 'topic' as const,
  options: { durable: true },
};

// Dead-letter args shared by workload queues
const DLQ_ARGS = {
  'x-dead-letter-exchange': 'dispatcher',
  'x-dead-letter-routing-key': 'dispatcher.dlq',
} as const;

// Retry queue args — no consumer. Messages sit here with per-message TTL,
// then dead-letter back to `dispatcher` exchange preserving their original RK.
const RETRY_QUEUE_ARGS = {
  'x-dead-letter-exchange': 'dispatcher',
  // NO x-dead-letter-routing-key — RK is preserved from original publish
} as const;

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env', '.env.local'],
    }),

    RabbitMQModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        uri:
          configService.get('RABBITMQ_URL') ||
          'amqp://agentforge:agentforge@localhost:5672',
        exchanges: [DISPATCHER_EXCHANGE, DISPATCHER_RETRY_EXCHANGE],
        queues: [
          // Workload queues
          {
            name: 'dispatcher.mail',
            options: { durable: true, arguments: DLQ_ARGS },
            exchange: 'dispatcher',
            routingKey: 'mail.dispatch',
          },
          {
            name: 'dispatcher.heavy',
            options: { durable: true, arguments: DLQ_ARGS },
            exchange: 'dispatcher',
            routingKey: 'heavy.dispatch',
          },
          {
            name: 'dispatcher.webhook',
            options: { durable: true, arguments: DLQ_ARGS },
            exchange: 'dispatcher',
            routingKey: 'webhook.dispatch',
          },
          {
            name: 'dispatcher.default',
            options: { durable: true, arguments: DLQ_ARGS },
            exchange: 'dispatcher',
            routingKey: 'default.dispatch',
          },
          // Retry holding queue — matches ALL routing keys, TTL per message
          {
            name: 'dispatcher.retry',
            options: { durable: true, arguments: RETRY_QUEUE_ARGS },
            exchange: 'dispatcher.retry',
            routingKey: '#',
          },
          // Dead letter queue — terminal state
          {
            name: 'dispatcher.dlq',
            options: { durable: true },
            exchange: 'dispatcher',
            routingKey: 'dispatcher.dlq',
          },
        ],
        connectionInitOptions: { wait: true },
        connectionManagerOptions: {
          heartbeatIntervalInSeconds: 30,
          reconnectTimeInSeconds: 5,
        },
      }),
    }),
  ],
  controllers: [HealthController, DispatchController],
  providers: [
    ServiceRegistry,
    HttpClientService,
    DispatcherConsumer,
    DispatchService,
    { provide: APP_GUARD, useClass: DispatcherAuthGuard },
  ],
})
export class AppModule {}
