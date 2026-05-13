import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as fs from 'fs';
import * as path from 'path';

interface RouteConfig {
  url: string;
  description?: string;
  // Per-service headers the dispatcher injects on every forwarded
  // request. Values can reference env vars with ``${VAR_NAME}`` so
  // secrets stay out of the JSON (resolved at load time). When the
  // env var is missing, the header is dropped (logged as a warning).
  header?: Record<string, string>;
}

interface RoutesFile {
  services: Record<string, RouteConfig>;
}

interface ServiceConfig {
  name: string;
  url: string;
  description?: string;
  header: Record<string, string>;
}

const ENV_PLACEHOLDER = /^\$\{([A-Z0-9_]+)\}$/;

/**
 * Service Registry
 *
 * Loads routes from routes.json with environment variable overrides.
 * Priority: ENV_VAR > routes.json
 *
 * Environment variable format: {SERVICE_NAME}_URL (e.g., API_URL, MAIL_URL)
 */
@Injectable()
export class ServiceRegistry implements OnModuleInit {
  private readonly logger = new Logger(ServiceRegistry.name);
  private readonly services: Map<string, ServiceConfig> = new Map();

  constructor(private readonly configService: ConfigService) {
    this.loadRoutes();
  }

  private loadRoutes(): void {
    const routesPath = path.join(__dirname, 'routes.json');

    try {
      const routesContent = fs.readFileSync(routesPath, 'utf-8');
      const routes: RoutesFile = JSON.parse(routesContent);

      for (const [name, config] of Object.entries(routes.services)) {
        // Environment variable override: API_URL, MEETING_API_URL, MAIL_URL, etc.
        const envKey = `${name.toUpperCase().replace(/-/g, '_')}_URL`;
        const url = this.configService.get<string>(envKey) || config.url;
        const header = this.resolveForwardHeaders(
          name,
          config.header ?? {},
        );

        this.services.set(name, {
          name,
          url,
          description: config.description,
          header,
        });
      }
    } catch (error) {
      this.logger.error(`Failed to load routes.json: ${error}`);
      throw error;
    }
  }

  onModuleInit() {
    this.validate();
    this.logger.log('Service Registry initialized');
    this.logger.log(`Registered services: ${this.listServicesFormatted()}`);
  }

  private validate(): void {
    const errors: string[] = [];

    for (const [name, config] of this.services) {
      if (!config.url) {
        errors.push(`Missing URL for service: ${name}`);
      }
    }

    if (errors.length > 0) {
      throw new Error(`Service Registry validation failed:\n${errors.join('\n')}`);
    }
  }

  private resolveForwardHeaders(
    serviceName: string,
    raw: Record<string, string>,
  ): Record<string, string> {
    const resolved: Record<string, string> = {};
    for (const [headerName, rawValue] of Object.entries(raw)) {
      const placeholder = ENV_PLACEHOLDER.exec(rawValue);
      const value = placeholder
        ? this.configService.get<string>(placeholder[1])
        : rawValue;
      if (!value) {
        // Either an env var is unset, or the literal value was empty.
        // Skip rather than send an empty Authorization-style header
        // that downstream guards would reject anyway.
        if (placeholder) {
          this.logger.warn(
            `Service ${serviceName}: header ${headerName} references ` +
              `env var ${placeholder[1]} which is not set — header omitted.`,
          );
        }
        continue;
      }
      resolved[headerName] = value;
    }
    return resolved;
  }

  getForwardHeaders(serviceName: string): Record<string, string> {
    const config = this.services.get(serviceName);
    return config ? { ...config.header } : {};
  }

  resolve(serviceName: string): string {
    const config = this.services.get(serviceName);

    if (!config) {
      throw new Error(
        `Unknown service: ${serviceName}. Available: ${this.listServiceNames()}`,
      );
    }

    return config.url;
  }

  buildUrl(serviceName: string, urlPath: string): string {
    const baseUrl = this.resolve(serviceName);
    const normalizedPath = urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
    return `${baseUrl}${normalizedPath}`;
  }

  has(serviceName: string): boolean {
    return this.services.has(serviceName);
  }

  listServices(): ServiceConfig[] {
    return Array.from(this.services.values());
  }

  private listServiceNames(): string {
    return Array.from(this.services.keys()).join(', ');
  }

  private listServicesFormatted(): string {
    return Array.from(this.services.values())
      .map((s) => `${s.name}=${s.url}`)
      .join(', ');
  }
}
