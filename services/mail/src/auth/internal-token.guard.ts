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
 * Validates `x-internal-token` against `INTERNAL_TOKEN` env var.
 * Skips health endpoints. Fail-closed in production: refuses to authorize
 * any request when secret is unset and NODE_ENV=production.
 */
@Injectable()
export class InternalTokenGuard implements CanActivate {
  private readonly logger = new Logger(InternalTokenGuard.name);
  private readonly secret: string | undefined;
  private readonly isProd: boolean;

  constructor(private readonly configService: ConfigService) {
    this.secret = this.configService.get<string>('INTERNAL_TOKEN');
    this.isProd = this.configService.get<string>('NODE_ENV') === 'production';

    if (!this.secret) {
      const msg = 'INTERNAL_TOKEN is not set — auth guard is disabled.';
      if (this.isProd) {
        this.logger.error(`${msg} Refusing to start in production.`);
        throw new Error('INTERNAL_TOKEN must be set when NODE_ENV=production');
      }
      this.logger.warn(`${msg} Set it in production.`);
    }
  }

  canActivate(context: ExecutionContext): boolean {
    if (!this.secret) return true;

    const request = context.switchToHttp().getRequest<Request>();
    const path = request.path || request.url;
    if (path.startsWith('/health')) return true;

    const token = request.headers['x-internal-token'] as string | undefined;
    if (!token || !this.safeEqual(token, this.secret)) {
      throw new UnauthorizedException('Invalid or missing internal token');
    }
    return true;
  }

  private safeEqual(a: string, b: string): boolean {
    if (a.length !== b.length) return false;
    let diff = 0;
    for (let i = 0; i < a.length; i++) {
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return diff === 0;
  }
}
