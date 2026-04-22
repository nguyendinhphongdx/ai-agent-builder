import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import * as https from 'https';
import type { DispatchMessage } from '../dispatch/dispatch.types';

// HTTPS agent that ignores self-signed certificates
const httpsAgent = new https.Agent({
  rejectUnauthorized: false,
});

export interface HttpResponse {
  success: boolean;
  status?: number;
  data?: unknown;
  error?: string;
  duration: number;
}

@Injectable()
export class HttpClientService {
  private readonly logger = new Logger(HttpClientService.name);
  private readonly defaultTimeout: number;

  constructor(private readonly configService: ConfigService) {
    this.defaultTimeout = this.configService.get('HTTP_TIMEOUT', 30000);
  }

  async request(url: string, message: DispatchMessage): Promise<HttpResponse> {
    const startTime = Date.now();
    const timeout = message.timeout || this.defaultTimeout;

    const config: AxiosRequestConfig = {
      url,
      method: message.method,
      headers: {
        ...message.headers,
        'x-source-service': message.source || 'dispatcher',
        'X-Dispatch-Id': message.id,
        'X-Dispatch-Source': message.source,
        'X-Dispatch-Event': message.event,
        ...(message.correlationId && {
          'X-Correlation-Id': message.correlationId,
        }),
      },
      data: message.body,
      timeout,
      validateStatus: () => true,
      httpsAgent,
    };

    try {
      const response = await axios(config);
      const duration = Date.now() - startTime;
      const success = response.status >= 200 && response.status < 300;

      if (success) {
        this.logger.log('Request succcess with status ' + response.status);
      } else {
        this.logger.warn(
          `HTTP request returned non-2xx status: ${response.status} for request ${message.id} to ${url} (duration: ${duration}ms)`
        );
      }

      return { success, status: response.status, data: response.data, duration };
    } catch (error) {
      const duration = Date.now() - startTime;
      const axiosError = error as AxiosError;

      this.logger.error({
        message: 'HTTP request failed',
        id: message.id,
        url,
        error: axiosError.message,
        duration,
      });

      return { success: false, error: axiosError.message, duration };
    }
  }
}
