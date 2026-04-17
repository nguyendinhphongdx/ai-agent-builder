import { Module } from '@nestjs/common';
import { ConnectionsModule } from '../connections/connections.module';
import { HealthController } from './health.controller';

@Module({
  imports: [ConnectionsModule],
  controllers: [HealthController],
})
export class HealthModule {}
