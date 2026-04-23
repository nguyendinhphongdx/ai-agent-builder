import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { appConfig, authConfig, redisConfig } from './config';
import { AuthModule } from './auth/auth.module';
import { ConnectionsModule } from './connections/connections.module';
import { GatewayModule } from './gateway/gateway.module';
import { EmitModule } from './emit/emit.module';
import { SessionModule } from './session/session.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [appConfig, authConfig, redisConfig],
    }),
    AuthModule,
    ConnectionsModule,
    GatewayModule,
    EmitModule,
    SessionModule,
    HealthModule,
  ],
})
export class AppModule {}
