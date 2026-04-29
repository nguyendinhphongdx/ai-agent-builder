import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import { Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Server, Socket } from 'socket.io';
import { JwtService } from '../auth/jwt.service';
import { ConnectionsService } from '../connections/connections.service';

@WebSocketGateway({
  cors: {
    // Resolved at request time against the allowlist populated in the gateway's
    // constructor (DI runs before any client connects).
    origin: (origin, cb) => {
      if (!origin || SocketGateway.allowedOrigins.includes(origin)) {
        cb(null, true);
      } else {
        cb(new Error('Origin not allowed'), false);
      }
    },
    credentials: true,
  },
})
export class SocketGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  static allowedOrigins: string[] = [];

  private readonly logger = new Logger(SocketGateway.name);

  constructor(
    private readonly jwt: JwtService,
    private readonly connections: ConnectionsService,
    config: ConfigService,
  ) {
    // Decorator runs before DI — capture origins on first instantiation so the
    // dynamic CORS callback can use them.
    SocketGateway.allowedOrigins = config.get<string[]>('app.corsOrigins') ?? [];
  }

  private short(id: string): string {
    return id.slice(0, 8);
  }

  handleConnection(client: Socket) {
    try {
      const token = client.handshake.auth?.token;
      if (!token) throw new Error('Missing token');

      const payload = this.jwt.verify(token);
      const userId = payload.sub;

      client.data.userId = userId;
      // Authoritative room set comes from the signed JWT — not from the client.
      const allowed = new Set<string>([`user:${userId}`, ...(payload.rooms ?? [])]);
      client.data.allowedRooms = allowed;
      for (const room of allowed) {
        client.join(room);
      }

      this.connections.add(userId, client.id);
      this.logger.log(
        `CONNECT   user=${this.short(userId)} sock=${this.short(client.id)}`,
      );
    } catch (err) {
      this.logger.warn(`REJECT    ${(err as Error).message}`);
      client.disconnect(true);
    }
  }

  handleDisconnect(client: Socket) {
    const userId = this.connections.remove(client.id);
    if (userId) {
      this.logger.log(
        `DISCONN   user=${this.short(userId)} sock=${this.short(client.id)}`,
      );
    }
  }

  @SubscribeMessage('join')
  handleJoin(client: Socket, data: { room: string }) {
    if (!data?.room) return;
    const allowed: Set<string> | undefined = client.data.allowedRooms;
    if (!allowed?.has(data.room)) {
      this.logger.warn(
        `JOIN-DENY user=${this.short(client.data.userId)} room=${data.room}`,
      );
      return;
    }
    client.join(data.room);
    this.logger.log(
      `JOIN      user=${this.short(client.data.userId)} room=${data.room}`,
    );
  }

  @SubscribeMessage('leave')
  handleLeave(client: Socket, data: { room: string }) {
    if (data?.room) {
      client.leave(data.room);
      this.logger.log(
        `LEAVE     user=${this.short(client.data.userId)} room=${data.room}`,
      );
    }
  }
}
