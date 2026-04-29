import { registerAs } from '@nestjs/config';

const isProd = process.env.NODE_ENV === 'production';

function requireSecret(name: string, fallback = 'change-me'): string {
  const value = process.env[name];
  if (!value || value === fallback) {
    if (isProd) {
      throw new Error(`${name} must be set when NODE_ENV=production`);
    }
    return fallback;
  }
  return value;
}

// Comma-separated list of allowed origins, e.g. "https://app.example.com,https://admin.example.com"
function parseOrigins(raw: string): string[] {
  return raw.split(',').map((o) => o.trim()).filter(Boolean);
}

export const appConfig = registerAs('app', () => ({
  port: parseInt(process.env.PORT ?? '4000', 10),
  corsOrigins: parseOrigins(process.env.CORS_ORIGIN ?? 'http://localhost:3000'),
  // Public URL clients connect to for the WebSocket handshake. Returned by
  // POST /session so backend callers never need to hardcode it.
  publicUrl: process.env.PUBLIC_URL ?? 'http://localhost:4000',
}));

export const authConfig = registerAs('auth', () => ({
  secretKey: requireSecret('SECRET_KEY'),
  algorithm: process.env.JWT_ALGORITHM ?? 'HS256',
  apiSecret: requireSecret('API_SECRET'),
}));

export const redisConfig = registerAs('redis', () => ({
  url: process.env.REDIS_URL ?? 'redis://localhost:6379/0',
}));
