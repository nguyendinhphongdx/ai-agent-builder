import { Module } from '@nestjs/common';
import { GatewayModule } from '../gateway/gateway.module';
import { EmitController } from './emit.controller';
import { EmitGuard } from './emit.guard';

@Module({
  imports: [GatewayModule],
  controllers: [EmitController],
  providers: [EmitGuard],
})
export class EmitModule {}
