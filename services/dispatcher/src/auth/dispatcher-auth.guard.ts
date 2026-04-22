import {
  CanActivate,
  ExecutionContext,
  Injectable,
  Logger,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { Request } from 'express';

/**
 * Dispatcher Auth Guard
 *
 * Validates `x-dispatcher-token` header against `DISPATCHER_SECRET` env var.
 *
 * Bypassed when `DISPATCHER_SECRET` is unset — useful for local dev with a single
 * machine, but should ALWAYS be set in production. Service logs a warning at boot
 * if secret is missing.
 *
 * Skips health endpoints (`/health`, `/healthz`, `/readyz`) so load balancers
 * can probe without credentials.
 */
@Injectable()
export class DispatcherAuthGuard implements CanActivate {
  private readonly logger = new Logger(DispatcherAuthGuard.name);
  private readonly secret: string | undefined;

  constructor(private readonly configService: ConfigService) {
    this.secret = this.configService.get<string>('DISPATCHER_SECRET');

    if (!this.secret) {
      this.logger.warn(
        'DISPATCHER_SECRET is not set — auth guard is disabled. Set it in production.',
      );
    }
  }

  canActivate(context: ExecutionContext): boolean {
    if (!this.secret) return true;

    const request = context.switchToHttp().getRequest<Request>();
    const path = request.path || request.url;

    if (this.isHealthEndpoint(path)) return true;

    const token =
      (request.headers['x-dispatcher-token'] as string | undefined) ??
      this.extractBearer(request.headers.authorization);

    if (!token || !this.safeEqual(token, this.secret)) {
      throw new UnauthorizedException('Invalid or missing dispatcher token');
    }

    return true;
  }

  private isHealthEndpoint(path: string): boolean {
    return path === '/health' || path === '/healthz' || path === '/readyz';
  }

  private extractBearer(header?: string): string | undefined {
    if (!header) return undefined;
    const [scheme, value] = header.split(' ');
    return scheme?.toLowerCase() === 'bearer' ? value : undefined;
  }

  /**
   * Constant-time comparison to prevent timing attacks on the secret.
   */
  private safeEqual(a: string, b: string): boolean {
    if (a.length !== b.length) return false;
    let diff = 0;
    for (let i = 0; i < a.length; i++) {
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return diff === 0;
  }
}
