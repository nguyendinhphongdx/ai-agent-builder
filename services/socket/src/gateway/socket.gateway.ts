import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import { Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { JwtService } from '../auth/jwt.service';
import { ConnectionsService } from '../connections/connections.service';

@WebSocketGateway({ cors: { origin: true, credentials: true } })
export class SocketGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(SocketGateway.name);

  constructor(
    private readonly jwt: JwtService,
    private readonly connections: ConnectionsService,
  ) {}

  handleConnection(client: Socket) {
    try {
      const token = client.handshake.auth?.token;
      if (!token) throw new Error('Missing token');

      const payload = this.jwt.verify(token);
      const userId = payload.sub;

      // Store userId on socket for later use
      client.data.userId = userId;

      // Join personal room
      client.join(`user:${userId}`);

      // Join rooms from token claims
      if (payload.rooms?.length) {
        for (const room of payload.rooms) {
          client.join(room);
        }
      }

      this.connections.add(userId, client.id);
      this.logger.log(`+ ${userId} (${client.id})`);
    } catch (err) {
      this.logger.warn(`Rejected: ${(err as Error).message}`);
      client.disconnect(true);
    }
  }

  handleDisconnect(client: Socket) {
    const userId = this.connections.remove(client.id);
    if (userId) {
      this.logger.log(`- ${userId} (${client.id})`);
    }
  }

  @SubscribeMessage('join')
  handleJoin(client: Socket, data: { room: string }) {
    if (data?.room) {
      client.join(data.room);
      this.logger.log(`${client.data.userId} joined ${data.room}`);
    }
  }

  @SubscribeMessage('leave')
  handleLeave(client: Socket, data: { room: string }) {
    if (data?.room) {
      client.leave(data.room);
      this.logger.log(`${client.data.userId} left ${data.room}`);
    }
  }
}
