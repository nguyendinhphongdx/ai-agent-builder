import { Controller, Get } from '@nestjs/common';
import { ServiceRegistry } from '../config/service-registry';

/**
 * Health check response
 */
interface HealthResponse {
  status: 'ok' | 'error';
  service: string;
  version: string;
  timestamp: string;
  uptime: number;
  services: Array<{ name: string; url: string }>;
}

/**
 * Health Controller
 *
 * Provides health check endpoints for monitoring and load balancers.
 */
@Controller()
export class HealthController {
  private readonly startTime = Date.now();

  constructor(private readonly serviceRegistry: ServiceRegistry) {}

  /**
   * Health check endpoint
   */
  @Get('health')
  health(): HealthResponse {
    return {
      status: 'ok',
      service: 'dispatcher',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      services: this.serviceRegistry.listServices(),
    };
  }

  /**
   * Liveness probe for Kubernetes
   */
  @Get('healthz')
  liveness(): { status: string } {
    return { status: 'ok' };
  }

  /**
   * Readiness probe for Kubernetes
   */
  @Get('readyz')
  readiness(): { status: string } {
    return { status: 'ok' };
  }
}
