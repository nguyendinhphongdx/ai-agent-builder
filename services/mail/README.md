# Mail Service

NestJS-based email microservice cho AgentForge. Gửi mail qua SendGrid với hỗ trợ Handlebars templates.

## Tổng quan

- **Framework**: NestJS 10 (TypeScript, ESM, Node 20)
- **Provider**: SendGrid (`@sendgrid/mail`)
- **Template engine**: Handlebars (`.hbs`)
- **Port**: `3011`
- **Container name**: `agentforge-mail`

Service chạy độc lập trong Docker network `agentforge` và chỉ nhận request từ các internal services khác (không expose public).

## Cấu trúc

```text
services/mail/
├── Dockerfile              # Multi-stage build (builder + production)
├── docker-compose.yml      # Container config + healthcheck
├── .env.example            # Template biến môi trường
├── nest-cli.json           # Copy templates vào dist khi build
├── package.json
├── test.html               # UI test nhanh (mở browser)
└── src/
    ├── main.ts             # Bootstrap NestJS, CORS dev-only, shutdown hooks
    ├── app.module.ts       # Wire ConfigModule, providers, controllers
    ├── config/
    │   └── mail.config.ts  # registerAs('mail', ...) — driver, from, SMTP, SendGrid
    ├── health/
    │   └── health.controller.ts   # GET /health, /healthz, /readyz
    ├── mail/
    │   ├── mail.controller.ts     # POST /mail/send, GET /mail/templates
    │   ├── mail.service.ts        # Render template -> gọi provider
    │   └── mail.types.ts          # MailMessage DTO
    ├── providers/
    │   ├── mail-provider.interface.ts   # MailProvider contract + DI token
    │   ├── mail-provider.module.ts      # Factory chọn provider theo MAIL_DRIVER
    │   ├── sendgrid.provider.ts         # SendGrid API
    │   ├── smtp.provider.ts             # nodemailer (Gmail, Zoho, Mailhog, SES SMTP...)
    │   └── console.provider.ts          # Log ra console — zero-config dev
    └── templates/
        ├── template.service.ts    # Load & compile .hbs khi module init
        └── templates/             # 1 template general (xem bên dưới)
```

## Biến môi trường

### Chung

| Tên | Mặc định | Mô tả |
| --- | --- | --- |
| `PORT` | `3011` | Port HTTP |
| `NODE_ENV` | `development` | `production` sẽ tắt CORS |
| `MAIL_DRIVER` | `sendgrid` | `sendgrid` / `smtp` / `console` — xem mục **Drivers** bên dưới |
| `MAIL_FROM` | `noreply@agentforge.com` | Địa chỉ `from` mặc định |
| `MAIL_FROM_NAME` | `AgentForge` | Tên hiển thị |

### SendGrid (`MAIL_DRIVER=sendgrid`)

| Tên | Mặc định | Mô tả |
| --- | --- | --- |
| `SENDGRID_API_KEY` | *(bắt buộc)* | SendGrid API key — thiếu thì service log error và mọi `send` fail |

### SMTP (`MAIL_DRIVER=smtp`)

| Tên | Mặc định | Mô tả |
| --- | --- | --- |
| `SMTP_HOST` | *(bắt buộc)* | vd: `smtp.gmail.com`, `smtp.zoho.com`, `mailhog`, `email-smtp.us-east-1.amazonaws.com` |
| `SMTP_PORT` | `587` | `587` (STARTTLS), `465` (SSL), `25` (unencrypted) |
| `SMTP_SECURE` | `false` | `true` cho port 465 |
| `SMTP_USER` | *(optional)* | Username — nếu rỗng thì không auth |
| `SMTP_PASS` | *(optional)* | Password hoặc app-specific password |

Tạo file `.env` từ `.env.example` trước khi chạy local.

## Chạy

### Docker (khuyến nghị)

```bash
docker network create agentforge   # một lần
cd services/mail
docker compose up -d
```

Healthcheck: `wget http://localhost:3011/health` mỗi 30s.

### Local dev

```bash
cd services/mail
pnpm install
cp .env.example .env        # rồi điền SENDGRID_API_KEY
pnpm dev                    # nest start --watch
```

Build production:

```bash
pnpm build                  # compile TS + copy templates vào dist/
pnpm start:prod
```

## HTTP API

Base URL: `http://agentforge-mail:3011` (trong network) hoặc `http://localhost:3011` (host).

### `GET /health`

Trả về status, uptime, và danh sách template đã load.

```json
{
  "status": "ok",
  "service": "mail-service",
  "version": "1.0.0",
  "timestamp": "2026-04-22T10:00:00.000Z",
  "uptime": 123,
  "templates": ["general", "welcome", "verification", "password-reset", "application-received", "application-status", "job-match"]
}
```

`GET /healthz` và `GET /readyz` trả về `{status: "ok"}` cho k8s liveness/readiness.

### `GET /mail/templates`

```json
{ "templates": ["general", "welcome", ...] }
```

### `POST /mail/send`

Request body ([MailMessage](src/mail/mail.types.ts)):

```json
{
  "to": "user@example.com",
  "subject": "Welcome!",
  "template": "welcome",
  "data": { "userName": "An", "profileUrl": "https://..." },
  "from": "custom@sender.com",
  "replyTo": "support@agentforge.com",
  "attachments": [
    { "filename": "file.pdf", "content": "<base64>", "contentType": "application/pdf" }
  ]
}
```

Rules:

- `to` chấp nhận string hoặc array.
- Nếu có `template`, service render bằng Handlebars với `data`. Nếu không, bắt buộc truyền `html` hoặc `text`.
- Template không tồn tại → `{ success: false, error: "Template not found: ..." }`.

Response ([MailResult](src/providers/mail-provider.interface.ts)):

```json
{ "success": true, "messageId": "x-message-id-from-sendgrid" }
```

hoặc:

```json
{ "success": false, "error": "..." }
```

## Templates có sẵn

Tất cả templates nằm ở [src/templates/templates/](src/templates/templates/) và tự load khi service khởi động.

Hiện service chỉ có **1 template đa dụng**:

### `general`

Template AgentForge-branded, layout responsive + MSO-safe (Outlook), dùng được cho mọi loại email (welcome, verification, password reset, notification...) bằng cách truyền HTML vào biến `content`.

**Biến nhận:**

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `title` | yes | Thẻ `<title>` của email (hiển thị ở tab preview) |
| `previewText` | no | Preview text trong inbox list (ẩn trong body) |
| `greeting` | no | Dòng chào đầu tiên, in đậm (vd: "Chào bạn,") |
| `content` | **yes** | HTML nội dung chính — render thô bằng `{{{content}}}` |
| `buttonText` | no | Label CTA button (bắt buộc nếu có `buttonUrl`) |
| `buttonUrl` | no | URL CTA button — không truyền thì không render button |
| `unsubscribeUrl` | no | Link huỷ đăng ký ở footer — không truyền thì ẩn |

Các block `buttonUrl`, `greeting`, `unsubscribeUrl` dùng `{{#if}}` nên đều optional.

### Handlebars helpers tự đăng ký

- `{{currentYear}}` — năm hiện tại
- `{{formatDate date}}` — format `en-US` long
- `{{#if (eq a b)}}` — so sánh `===`

### Thêm template mới

1. Tạo file `src/templates/templates/<name>.hbs`.
2. Restart service — `TemplateService.onModuleInit` sẽ compile và load.
3. Dùng bằng cách truyền `"template": "<name>"` trong `POST /mail/send`.

## Drivers

Service chọn provider runtime dựa trên biến `MAIL_DRIVER`. Factory nằm trong [mail-provider.module.ts](src/providers/mail-provider.module.ts) — `app.module.ts` chỉ import module, không chứa logic chọn driver.

| Driver | Use case | Config cần thiết |
| --- | --- | --- |
| `console` | Local dev, CI, debug template | Không cần gì — zero-config |
| `smtp` | Gmail, Zoho, Mailhog/Mailtrap, SES SMTP, self-hosted | `SMTP_HOST` + optional auth |
| `sendgrid` | Production với SendGrid | `SENDGRID_API_KEY` |

### `console` driver

Log email ra terminal thay vì gửi. Dùng cho local dev không cần API key hoặc khi muốn debug nhanh. Response trả về `success: true` với `messageId` dạng `console-<timestamp>-<random>`.

### `smtp` driver

Dùng [`nodemailer`](https://nodemailer.com) — cover được mọi SMTP server. Một số config mẫu:

**Gmail** (cần [app-specific password](https://myaccount.google.com/apppasswords)):

```env
MAIL_DRIVER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx
```

**Mailhog** (local sandbox, `docker run mailhog/mailhog`):

```env
MAIL_DRIVER=smtp
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_SECURE=false
```

**AWS SES SMTP**:

```env
MAIL_DRIVER=smtp
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=<SES_SMTP_USERNAME>
SMTP_PASS=<SES_SMTP_PASSWORD>
```

### `sendgrid` driver

Original implementation, dùng `@sendgrid/mail` SDK. Xem [hướng dẫn lấy API key](https://docs.sendgrid.com/for-developers/sending-email/api-getting-started).

### Thêm provider mới

`MailProvider` interface ([mail-provider.interface.ts](src/providers/mail-provider.interface.ts)) chỉ có 1 method:

```ts
export interface MailProvider {
  send(options: SendMailOptions): Promise<MailResult>;
}
```

Các bước thêm provider (vd: `resend`):

1. Tạo `src/providers/resend.provider.ts` implement `MailProvider`.
2. Thêm vào `SUPPORTED_DRIVERS` và `createProvider()` switch trong [mail-provider.module.ts](src/providers/mail-provider.module.ts).
3. Export từ [providers/index.ts](src/providers/index.ts).
4. Update `.env.example` với biến config mới.

## Testing nhanh

Mở [test.html](test.html) trực tiếp trong browser — form UI để test gửi mail với template hoặc HTML tuỳ ý. Service URL mặc định `http://localhost:3011`.

## Resource limits

Docker compose giới hạn 256M memory, reserve 128M. Service nhẹ, không có state, restart-safe (`restart: unless-stopped`).
