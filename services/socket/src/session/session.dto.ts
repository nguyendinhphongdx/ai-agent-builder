import { IsArray, IsOptional, IsString } from 'class-validator';

export class CreateSessionDto {
  /** User ID that will be embedded in the JWT `sub` claim. */
  @IsString()
  userId!: string;

  /** Rooms the user is authorized to auto-join after handshake. */
  @IsArray()
  @IsOptional()
  rooms?: string[];

  /** TTL in seconds for the handshake JWT. Defaults to 60s server-side. */
  @IsOptional()
  ttlSeconds?: number;
}

export interface SessionResponse {
  /** WebSocket URL the client should connect to. */
  url: string;
  /** Short-lived JWT to pass as `auth.token` during handshake. */
  token: string;
  /** Seconds until the token expires. */
  expiresIn: number;
}
