import { Injectable } from '@nestjs/common';

@Injectable()
export class ConnectionsService {
  private readonly userToSockets = new Map<string, Set<string>>();
  private readonly socketToUser = new Map<string, string>();

  add(userId: string, socketId: string): void {
    const sockets = this.userToSockets.get(userId) ?? new Set<string>();
    sockets.add(socketId);
    this.userToSockets.set(userId, sockets);
    this.socketToUser.set(socketId, userId);
  }

  remove(socketId: string): string | null {
    const userId = this.socketToUser.get(socketId);
    if (!userId) {
      return null;
    }

    this.socketToUser.delete(socketId);
    const sockets = this.userToSockets.get(userId);
    if (!sockets) {
      return userId;
    }

    sockets.delete(socketId);
    if (sockets.size === 0) {
      this.userToSockets.delete(userId);
    }

    return userId;
  }

  getConnectedUsersCount(): number {
    return this.userToSockets.size;
  }

  getConnectionsCount(): number {
    return this.socketToUser.size;
  }

  snapshot(): Record<string, string[]> {
    const result: Record<string, string[]> = {};

    for (const [userId, sockets] of this.userToSockets.entries()) {
      result[userId] = Array.from(sockets);
    }

    return result;
  }
}