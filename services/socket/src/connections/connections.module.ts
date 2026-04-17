import { Module } from '@nestjs/common';
import { ConnectionsService } from './connections.service';

@Module({
  providers: [ConnectionsService],
  exports: [ConnectionsService],
})
export class ConnectionsModule {}
