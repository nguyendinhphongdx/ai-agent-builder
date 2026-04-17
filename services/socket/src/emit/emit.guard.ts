import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class EmitGuard implements CanActivate {
  private readonly apiSecret: string;

  constructor(config: ConfigService) {
    this.apiSecret = config.get<string>('auth.apiSecret', 'change-me');
  }

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return request.headers['x-api-secret'] === this.apiSecret;
  }
}
