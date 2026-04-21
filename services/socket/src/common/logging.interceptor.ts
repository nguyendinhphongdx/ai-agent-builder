import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  Logger,
} from '@nestjs/common';
import { Observable, tap } from 'rxjs';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('HTTP');

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    const res = context.switchToHttp().getResponse();
    const { method, url, body } = req;
    const start = Date.now();

    return next.handle().pipe(
      tap(() => {
        const ms = Date.now() - start;
        const status = res.statusCode;
        const pad = (s: string, n: number) => s.padEnd(n);

        // Format: METHOD  URL                        200  3ms  body
        const line = `${pad(method, 6)} ${pad(url, 26)} ${status} ${ms}ms`;
        const bodyStr = this.formatBody(body);
        this.logger.log(bodyStr ? `${line}  ${bodyStr}` : line);
      }),
    );
  }

  private formatBody(body: any): string {
    if (!body || Object.keys(body).length === 0) return '';
    try {
      const str = JSON.stringify(body);
      return str.length > 120 ? str.slice(0, 120) + '…' : str;
    } catch {
      return '';
    }
  }
}
