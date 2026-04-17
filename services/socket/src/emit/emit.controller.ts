import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { SocketGateway } from '../gateway/socket.gateway';
import { EmitGuard } from './emit.guard';
import { EmitToUserDto, EmitToRoomDto, BroadcastDto } from './emit.dto';

function envelope(event: string, payload: Record<string, unknown>) {
  return { event, payload, timestamp: new Date().toISOString() };
}

@Controller('emit')
@UseGuards(EmitGuard)
export class EmitController {
  constructor(private readonly gateway: SocketGateway) {}

  @Post()
  emitToUser(@Body() dto: EmitToUserDto) {
    this.gateway.server
      .to(`user:${dto.userId}`)
      .emit(dto.event, envelope(dto.event, dto.payload));
    return { ok: true };
  }

  @Post('room')
  emitToRoom(@Body() dto: EmitToRoomDto) {
    this.gateway.server
      .to(dto.room)
      .emit(dto.event, envelope(dto.event, dto.payload));
    return { ok: true };
  }

  @Post('broadcast')
  broadcast(@Body() dto: BroadcastDto) {
    this.gateway.server.emit(dto.event, envelope(dto.event, dto.payload));
    return { ok: true };
  }
}
