import { Module } from '@nestjs/common';
import { AuthModule } from '../auth/auth.module';
import { EmitGuard } from '../emit/emit.guard';
import { SessionController } from './session.controller';

@Module({
  imports: [AuthModule],
  controllers: [SessionController],
  providers: [EmitGuard],
})
export class SessionModule {}
