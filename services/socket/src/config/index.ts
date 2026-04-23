import { registerAs } from '@nestjs/config';

export const appConfig = registerAs('app', () => ({
  port: parseInt(process.env.PORT ?? '4000', 10),
  corsOrigin: process.env.CORS_ORIGIN ?? 'http://localhost:3000',
  // Public URL clients connect to for the WebSocket handshake. Returned by
  // POST /session so backend callers never need to hardcode it.
  publicUrl: process.env.PUBLIC_URL ?? 'http://localhost:4000',
}));

export const authConfig = registerAs('auth', () => ({
  secretKey: process.env.SECRET_KEY ?? 'change-me',
  algorithm: process.env.JWT_ALGORITHM ?? 'HS256',
  apiSecret: process.env.API_SECRET ?? 'change-me',
}));

export const redisConfig = registerAs('redis', () => ({
  url: process.env.REDIS_URL ?? 'redis://localhost:6379/0',
}));
