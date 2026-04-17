import { IsString, IsOptional, IsObject } from 'class-validator';

export class EmitToUserDto {
  @IsString()
  userId: string;

  @IsString()
  event: string;

  @IsObject()
  payload: Record<string, unknown>;
}

export class EmitToRoomDto {
  @IsString()
  room: string;

  @IsString()
  event: string;

  @IsObject()
  payload: Record<string, unknown>;
}

export class BroadcastDto {
  @IsString()
  event: string;

  @IsObject()
  payload: Record<string, unknown>;
}
