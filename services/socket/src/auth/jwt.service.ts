import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { sign, verify, JwtPayload } from 'jsonwebtoken';

export interface SocketTokenPayload extends JwtPayload {
  sub: string;
  type: 'socket';
  rooms?: string[];
}

@Injectable()
export class JwtService {
  private readonly secretKey: string;
  private readonly algorithm: string;

  constructor(private readonly config: ConfigService) {
    this.secretKey = this.config.get<string>('auth.secretKey', 'change-me');
    this.algorithm = this.config.get<string>('auth.algorithm', 'HS256');
  }

  /**
   * Mint a short-lived socket handshake token. Default TTL 60s.
   */
  sign(sub: string, rooms: string[] = [], ttlSeconds: number = 60): string {
    const payload: Omit<SocketTokenPayload, 'iat' | 'exp'> = {
      sub,
      type: 'socket',
      rooms,
    };
    return sign(payload as object, this.secretKey, {
      algorithm: this.algorithm as 'HS256',
      expiresIn: ttlSeconds,
    });
  }

  verify(token: string): SocketTokenPayload {
    const payload = verify(token, this.secretKey, {
      algorithms: [this.algorithm as 'HS256'],
    });

    if (typeof payload === 'string') {
      throw new Error('Invalid token payload');
    }

    const typed = payload as SocketTokenPayload;

    if (typed.type !== 'socket') {
      throw new Error('Invalid token type');
    }

    if (!typed.sub) {
      throw new Error('Missing user id');
    }

    return typed;
  }
}
