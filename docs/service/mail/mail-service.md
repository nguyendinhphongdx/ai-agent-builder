---
id: service-mail
title: Mail Service
domain: service
tags: [mail, email, sendgrid, smtp, nodemailer, nestjs, microservice, handlebars, templates, multi-provider]
related: [backend-auth, flows-user-registration]
summary: Standalone NestJS microservice on port 3011 that sends emails via pluggable providers (SendGrid, SMTP, Console) selected by MAIL_DRIVER env var. Exposes POST /mail/send with a single AgentForge-branded Handlebars template.
---

# Mail Service

## Overview

Mail Service là một microservice NestJS độc lập, chịu trách nhiệm gửi email cho toàn bộ platform AgentForge. Service được tách riêng để:

- **Cô lập provider**: Đổi SendGrid → SES/Mailgun chỉ cần thay implementation, không đụng backend chính.
- **Template hoá**: Không rải HTML template trong Python backend; tất cả template Handlebars tập trung ở một nơi.
- **Giới hạn resource**: Email là tác vụ I/O nặng và có thể rate-limit bởi provider; tách ra dễ scale độc lập.
- **Internal-only**: Chỉ nhận request từ các service trong Docker network `agentforge`, không expose public.

Đường dẫn source: [services/mail/](../../../services/mail/). Chi tiết vận hành xem [services/mail/README.md](../../../services/mail/README.md).

## Specification

### Runtime

| Attribute | Value |
| --- | --- |
| Framework | NestJS 10 (ESM, Node 20 Alpine) |
| Port | `3011` |
| Container | `agentforge-mail` |
| Network | `agentforge` (external Docker network) |
| Drivers | `sendgrid` (default), `smtp` (nodemailer), `console` (dev) |
| Template engine | Handlebars v4 |
| Memory limit | 256M (reserve 128M) |
| Healthcheck | `wget http://localhost:3011/health` mỗi 30s |

### Environment Variables

Chung:

| Biến | Bắt buộc | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `PORT` | no | `3011` | HTTP port |
| `NODE_ENV` | no | `development` | `production` tắt CORS |
| `MAIL_DRIVER` | no | `sendgrid` | `sendgrid` / `smtp` / `console` |
| `MAIL_FROM` | no | `noreply@agentforge.com` | Sender email mặc định |
| `MAIL_FROM_NAME` | no | `AgentForge` | Sender display name |
| `RETRY_MAX_ATTEMPTS` | no | `3` | Reserved (chưa hook vào) |
| `RETRY_BACKOFF_MS` | no | `2000` | Reserved |
| `RETRY_BACKOFF_MULTIPLIER` | no | `2` | Reserved |

Driver-specific (chỉ cần biến của driver đang dùng):

| Biến | Bắt buộc khi | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `SENDGRID_API_KEY` | `MAIL_DRIVER=sendgrid` | — | SendGrid API key |
| `SMTP_HOST` | `MAIL_DRIVER=smtp` | — | SMTP server hostname |
| `SMTP_PORT` | no | `587` | `587` (STARTTLS) / `465` (SSL) / `25` |
| `SMTP_SECURE` | no | `false` | `true` cho port 465 |
| `SMTP_USER` | no | — | SMTP auth username (rỗng → không auth) |
| `SMTP_PASS` | no | — | SMTP auth password |

### Module Structure

Service dùng 4-layer chuẩn NestJS (controller → service → provider → template) với DI token-based provider injection. Logic chọn driver được đóng gói trong `MailProviderModule` để `app.module.ts` chỉ import module mà không chứa branching:

```text
AppModule
├── ConfigModule.forRoot({ load: [mailConfig], envFilePath: ['.env.local', '.env'] })
├── MailProviderModule                 // expose MAIL_PROVIDER token
│   └── useFactory(config) -> switch(MAIL_DRIVER):
│       ├── 'sendgrid' → new SendGridProvider(config)
│       ├── 'smtp'     → new SmtpProvider(config)
│       └── 'console'  → new ConsoleProvider()
├── Controllers
│   ├── HealthController               // GET /health, /healthz, /readyz
│   └── MailController                 // POST /mail/send, GET /mail/templates
└── Providers
    ├── TemplateService                // OnModuleInit → load all .hbs files
    └── MailService                    // orchestrator (@Inject(MAIL_PROVIDER))
```

`MAIL_PROVIDER` là DI token (string `'MAIL_PROVIDER'`). `MailService` inject qua `@Inject(MAIL_PROVIDER)` nên hoàn toàn không biết driver nào đang chạy — chỉ thấy `MailProvider` interface.

### HTTP API

Base URL internal: `http://agentforge-mail:3011`.

#### `GET /health`

```json
{
  "status": "ok",
  "service": "mail-service",
  "version": "1.0.0",
  "timestamp": "2026-04-22T10:00:00.000Z",
  "uptime": 123,
  "templates": ["general"]
}
```

`GET /healthz` và `GET /readyz` → `{status: "ok"}` (k8s-compatible).

#### `GET /mail/templates`

```json
{ "templates": ["general"] }
```

#### `POST /mail/send`

Request body (`MailMessage`):

```ts
interface MailMessage {
  to: string | string[];              // single email or list
  subject: string;
  template?: string;                  // key of .hbs template (optional)
  data?: Record<string, unknown>;     // variables for Handlebars
  html?: string;                      // raw HTML (used when no template)
  text?: string;                      // plain text fallback
  from?: string;                      // override MAIL_FROM
  replyTo?: string;
  attachments?: Attachment[];
  priority?: 'high' | 'normal' | 'low';  // accepted but not propagated to SendGrid
}

interface Attachment {
  filename: string;
  content?: string | Buffer;          // base64 string or Buffer (Buffer auto-encoded)
  path?: string;                      // not used by SendGrid provider
  contentType?: string;
}
```

Response (`MailResult`):

```ts
interface MailResult {
  success: boolean;
  messageId?: string;    // x-message-id header from SendGrid (on success)
  error?: string;        // on failure
}
```

Validation rules (enforced in [mail.service.ts](../../../services/mail/src/mail/mail.service.ts)):

- Nếu có `template` mà key không tồn tại → `{ success: false, error: "Template not found: <name>" }`.
- Nếu không có `template` và cả `html`/`text` đều rỗng → `{ success: false, error: "Email must have either html or text content" }`.
- Provider error (SendGrid API error) → `{ success: false, error: <message> }`.

Controller luôn trả HTTP 200 — caller phải check `success` field.

### Templates

Load tự động từ [services/mail/src/templates/templates/](../../../services/mail/src/templates/templates/) khi `TemplateService.onModuleInit` chạy. File `.hbs` → key = tên file (bỏ extension).

Service hiện chỉ có **1 template đa dụng** là `general`. Thay vì maintain nhiều template chuyên biệt cho từng loại email (welcome / verification / password-reset / notification...), backend compose HTML vào biến `content` và dùng lại cùng layout AgentForge-branded. Lý do:

- **Đồng nhất branding** — mọi email đều có cùng header/footer, logo gradient, typography.
- **Ít bảo trì** — fix layout 1 chỗ áp dụng cho tất cả loại email.
- **Linh hoạt** — backend tự quyết định nội dung HTML; không bị giới hạn bởi biến template cứng.

#### `general`

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `title` | yes | `<title>` của email (hiển thị tab preview) |
| `previewText` | no | Preview text inbox (ẩn trong body) |
| `greeting` | no | Dòng chào in đậm đầu content (`{{#if greeting}}`) |
| `content` | **yes** | HTML nội dung chính — render thô qua `{{{content}}}` |
| `buttonText` | no | Label CTA button (bắt buộc khi có `buttonUrl`) |
| `buttonUrl` | no | CTA button URL — không truyền → không render button |
| `unsubscribeUrl` | no | Link huỷ đăng ký footer — không truyền → ẩn link |

Layout:

- Responsive breakpoint 620px.
- MSO-safe (Outlook) với conditional comments + table-based layout.
- Logo gradient indigo → purple khớp với brand AgentForge.
- Footer chứa link GitHub, Docs, Privacy, Unsubscribe (optional).
- Ghi chú "Email này được gửi tự động, vui lòng không reply trực tiếp."

#### Thêm template mới

Nếu cần template với layout khác hẳn (vd: invoice, digest), tạo thêm file `.hbs`:

1. Tạo `services/mail/src/templates/templates/<name>.hbs`.
2. `nest-cli.json` có `assets: ["templates/**/*"]` + `watchAssets: true` → dev mode hot-reload; production cần rebuild.
3. Gọi bằng `"template": "<name>"` trong request body.

Nhưng cho các use-case chuẩn (welcome, verify, reset password, notification), hãy dùng `general` + compose `content` từ backend.

#### Registered Handlebars helpers

- `{{currentYear}}` → `new Date().getFullYear()`
- `{{formatDate date}}` → `en-US` long format (`March 5, 2026`)
- `{{#if (eq a b)}}` → strict equality

### Provider abstraction

[mail-provider.interface.ts](../../../services/mail/src/providers/mail-provider.interface.ts):

```ts
export interface MailProvider {
  send(options: SendMailOptions): Promise<MailResult>;
}
export const MAIL_PROVIDER = 'MAIL_PROVIDER';
```

Thêm provider mới:

1. Implement `MailProvider` interface trong `src/providers/<name>.provider.ts`.
2. Thêm case vào `SUPPORTED_DRIVERS` + `createProvider()` trong [mail-provider.module.ts](../../../services/mail/src/providers/mail-provider.module.ts).
3. Export từ [providers/index.ts](../../../services/mail/src/providers/index.ts).
4. Bổ sung biến `.env.example`.

Không cần sửa `MailService` hay controllers.

### Driver-specific notes

**`SendGridProvider`** ([sendgrid.provider.ts](../../../services/mail/src/providers/sendgrid.provider.ts)):

- `text` default = `' '` (1 space) khi không truyền — SendGrid yêu cầu có `text` hoặc `html`.
- Attachments: `content` là string → gửi nguyên; `Buffer` → auto-encode base64.
- Ghi `messageId` từ response header `x-message-id`.

**`SmtpProvider`** ([smtp.provider.ts](../../../services/mail/src/providers/smtp.provider.ts)):

- Dùng `nodemailer` `createTransport` với auth chỉ khi có `SMTP_USER` + `SMTP_PASS` (trường hợp Mailhog không cần auth).
- Attachments pass-through trực tiếp — `nodemailer` tự handle string / Buffer / path.
- `messageId` lấy từ `info.messageId` của nodemailer.

**`ConsoleProvider`** ([console.provider.ts](../../../services/mail/src/providers/console.provider.ts)):

- Không gửi mail thật — chỉ log ra NestJS logger.
- `messageId` dạng `console-<timestamp>-<random6chars>`.
- Dùng cho local dev (không cần API key / SMTP server) và CI tests.

## Integration với Backend

Backend (FastAPI, Python) gọi mail service qua HTTP nội bộ:

```python
# Ví dụ (không phải code thật trong repo)
import httpx

async def send_verification_email(email: str, token: str):
    verify_link = f"https://app.agentforge.com/verify?token={token}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://agentforge-mail:3011/mail/send",
            json={
                "to": email,
                "subject": "Xác thực email AgentForge",
                "template": "general",
                "data": {
                    "title": "Xác thực email của bạn",
                    "previewText": "Một bước nữa để hoàn tất đăng ký AgentForge",
                    "greeting": "Chào bạn,",
                    "content": (
                        "<p>Nhấn nút bên dưới để xác thực email và kích hoạt tài khoản AgentForge của bạn.</p>"
                        "<p style=\"color:#71717a;font-size:13px\">Link sẽ hết hạn sau 24 giờ. "
                        "Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này.</p>"
                    ),
                    "buttonText": "Xác thực email",
                    "buttonUrl": verify_link,
                },
            },
            timeout=10.0,
        )
        result = resp.json()
        if not result["success"]:
            logger.error(f"Mail send failed: {result['error']}")
```

**Lưu ý**:

- Service URL dùng container name `agentforge-mail` (DNS trong Docker network). Từ host dùng `localhost:3011`.
- Luôn check `result["success"]` — HTTP status luôn 200.
- Không retry từ caller cho lỗi validation (template not found, empty content); chỉ retry lỗi transient từ SendGrid.

## Testing

File [test.html](../../../services/mail/test.html) là UI đơn giản (mở trực tiếp trong browser) để test gửi mail với template hoặc HTML thô. Mặc định trỏ `http://localhost:3011`.

## Related

- [backend-auth](../../backend/auth.md) — flow đăng ký/reset password sẽ gọi mail service.
- [flows-user-registration](../../flows/user-registration.md) — end-to-end registration sử dụng template `general` để gửi verification email.
