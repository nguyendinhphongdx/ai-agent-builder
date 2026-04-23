import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { EmitGuard } from '../emit/emit.guard';
import { JwtService } from '../auth/jwt.service';
import { CreateSessionDto } from './session.dto';
import type { SessionResponse } from './session.dto';

/**
 * Session endpoint — returns the data the frontend needs to open a socket:
 * public URL + short-lived JWT with the caller-declared room claims.
 *
 * Guarded by `x-api-secret` (same as /emit), so only trusted services (dispatcher,
 * backend via dispatcher) can mint tokens. Callers decide which rooms a user
 * may join; the socket service enforces claims on connect.
 */
@Controller('session')
@UseGuards(EmitGuard)
export class SessionController {
  constructor(
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
  ) {}

  @Post()
  create(@Body() body: CreateSessionDto): SessionResponse {
    const ttl = body.ttlSeconds ?? 60;
    const token = this.jwt.sign(body.userId, body.rooms ?? [], ttl);
    const url = this.config.get<string>('app.publicUrl', 'http://localhost:4000');
    return { url, token, expiresIn: ttl };
  }
}
