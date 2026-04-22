import { registerAs } from '@nestjs/config';

export default registerAs('mail', () => ({
  driver: process.env.MAIL_DRIVER || 'sendgrid',
  from: process.env.MAIL_FROM || 'noreply@agentforge.com',
  fromName: process.env.MAIL_FROM_NAME || 'AgentForge',
  sendgrid: {
    apiKey: process.env.SENDGRID_API_KEY,
  },
  smtp: {
    host: process.env.SMTP_HOST,
    port: parseInt(process.env.SMTP_PORT || '587', 10),
    secure: process.env.SMTP_SECURE === 'true',
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
  retry: {
    maxAttempts: parseInt(process.env.RETRY_MAX_ATTEMPTS || '3', 10),
    backoffMs: parseInt(process.env.RETRY_BACKOFF_MS || '2000', 10),
    backoffMultiplier: parseInt(process.env.RETRY_BACKOFF_MULTIPLIER || '2', 10),
  },
}));
