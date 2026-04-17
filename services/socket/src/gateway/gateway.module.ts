import { Module } from '@nestjs/common';
import { AuthModule } from '../auth/auth.module';
import { ConnectionsModule } from '../connections/connections.module';
import { SocketGateway } from './socket.gateway';

@Module({
  imports: [AuthModule, ConnectionsModule],
  providers: [SocketGateway],
  exports: [SocketGateway],
})
export class GatewayModule {}
