import { Controller, Get } from '@nestjs/common';
import { ConnectionsService } from '../connections/connections.service';

@Controller('health')
export class HealthController {
  constructor(private readonly connections: ConnectionsService) {}

  @Get()
  check() {
    return {
      status: 'ok',
      users: this.connections.getConnectedUsersCount(),
      connections: this.connections.getConnectionsCount(),
    };
  }
}
