"""Admin-facing service for the ``payment_provider_configs`` table.

Thin wrapper over :mod:`app.modules.commerce.payments.config` that
shapes rows for the admin grid: masks secrets, exposes per-provider
metadata (which keys are expected), and routes test-connection calls.

Why mask instead of omitting: the admin grid needs to know *that* a
key was entered before (so the operator doesn't accidentally wipe a
configured row), but the plaintext must never leave the API.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.modules.commerce.payments.config import (
    ProviderConfig,
    delete_provider_config,
    get_provider_config,
    list_provider_configs,
    test_provider_connection,
    upsert_provider_config,
)
from app.platform.config import settings

# Per-provider key catalogue — what the FE should render input fields
# for. Each entry: (key, label, hint). Secrets get a password field +
# masking; non-secrets render plain. Hints are short, one-line copy
# rendered under the input — long-form prose lives in PROVIDER_GUIDES.
PROVIDER_SECRET_KEYS: dict[str, list[tuple[str, str, str]]] = {
    "stripe": [
        ("secret_key", "Secret key", "Bắt đầu bằng sk_test_… (test mode) hoặc sk_live_… (production). Lấy ở Dashboard → Developers → API keys."),
        ("publishable_key", "Publishable key", "Bắt đầu bằng pk_test_… / pk_live_…. Dùng cho Stripe.js ở frontend — không bắt buộc nếu không nhúng Checkout vào FE."),
        ("webhook_secret", "Webhook signing secret", "Bắt đầu bằng whsec_…. Stripe chỉ hiển thị 1 lần khi tạo endpoint webhook — phải copy ngay, mất là tạo lại."),
    ],
    "momo": [
        ("partner_code", "Partner Code", "MoMo cấp khi tài khoản Business được duyệt. Định danh merchant của bạn."),
        ("access_key", "Access Key", "Cấp cùng Partner Code khi đăng ký Business. Dùng để định danh request gửi sang MoMo."),
        ("secret_key", "Secret Key", "Dùng để ký HMAC-SHA256 cho mọi request (create + refund) và xác thực IPN MoMo gửi về. Tuyệt đối không để lộ."),
    ],
}

PROVIDER_CONFIG_KEYS: dict[str, list[tuple[str, str, str]]] = {
    "stripe": [
        ("platform_fee_bps", "Phí nền tảng (basis points)", "Mặc định 1500 = 15%. Áp dụng dưới dạng application_fee cho Connect destination charge. 100 bps = 1% — chỉnh cẩn thận vì tác giả thấy ngay trên payout."),
        ("success_url", "URL thành công (Hub)", "Trang buyer được redirect sau khi mua template thành công. Có thể dùng placeholder {CHECKOUT_SESSION_ID}."),
        ("cancel_url", "URL hủy (Hub)", "Trang buyer được redirect khi bấm Cancel trong Stripe Checkout."),
        ("connect_return_url", "Connect — URL kết thúc onboarding", "Trang tác giả được redirect sau khi hoàn tất onboarding Stripe Connect."),
        ("connect_refresh_url", "Connect — URL refresh onboarding", "Stripe gọi nếu link onboarding hết hạn — thường point về cùng trang tạo link mới."),
        ("billing_success_url", "URL thành công (Subscription)", "Trang sau khi org admin checkout gói Subscription thành công."),
        ("billing_cancel_url", "URL hủy (Subscription)", "Trang khi admin bỏ giữa chừng flow nâng gói."),
    ],
    "momo": [
        ("endpoint", "MoMo API endpoint", "Sandbox: https://test-payment.momo.vn — Production: https://payment.momo.vn. Phải khớp với cờ Test mode bên trên."),
        ("notify_url", "IPN Notify URL", "URL MoMo POST kết quả thanh toán về. Đăng ký y hệt URL hiển thị ở Webhook bên dưới với MoMo Business."),
        ("return_url", "Browser Return URL", "Trang FE mà MoMo redirect trình duyệt buyer về sau khi thanh toán xong. Trang này nên poll /api/purchase-status để hiển thị kết quả."),
    ],
}

# Friendly default labels + kinds for the "not yet configured" entries
# we synthesise when an admin opens the page on a fresh deploy. Keep
# the codes in sync with the constants in `models.payment_provider_config`.
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "stripe": {"display_name": "Stripe", "kind": "both"},
    "momo": {"display_name": "MoMo", "kind": "paid"},
}


# Long-form setup guides surfaced as a collapsible block at the top of
# each editor. The FE renders sections sequentially, each with a title
# and a numbered step list. Webhook block lists the events / behaviour
# the provider expects, so admins copy the URL into the dashboard
# without flipping back to docs.
PROVIDER_GUIDES: dict[str, dict[str, Any]] = {
    "stripe": {
        "intro": (
            "Stripe phụ trách 2 luồng: **Hub** (mua template lẻ — USD/EUR/…) "
            "và **Subscription** (gói trả phí org). Cùng 1 secret key + 1 "
            "webhook URL phục vụ cả hai — backend tự routing theo prefix "
            "event của Stripe nên không cần config riêng."
        ),
        "requirements": [
            "Tài khoản Stripe (đăng ký tại stripe.com — Vietnam có thể đăng ký qua Stripe Atlas hoặc dùng tài khoản pháp nhân nước ngoài).",
            "Domain HTTPS công khai cho deployment — Stripe yêu cầu webhook endpoint phải là HTTPS, không dùng được localhost cho production.",
            "Nếu bán template qua Hub: cần bật Stripe Connect (Settings → Connect → Get started). Express accounts là loại được dùng.",
        ],
        "webhook": {
            "path": "/api/webhooks/stripe",
            "events": [
                "checkout.session.completed",
                "checkout.session.expired",
                "account.updated",
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "customer.subscription.trial_will_end",
                "invoice.payment_succeeded",
                "invoice.payment_failed",
            ],
            "note": (
                "Stripe sẽ retry với exponential backoff trong 3 ngày nếu "
                "endpoint trả non-2xx — không cần lo xử lý retry, chỉ cần "
                "đảm bảo handler idempotent. Backend đã dedupe theo event.id."
            ),
        },
        "sections": [
            {
                "title": "Bước 1 — Lấy API keys",
                "steps": [
                    "Đăng nhập dashboard.stripe.com, vào Developers → API keys.",
                    "Bật **Test mode** (góc trên phải dashboard) để lấy bộ key sk_test_… + pk_test_… trước. Triển khai đến lúc nào ổn rồi mới quay lại đây tắt Test mode + dán key live.",
                    "Copy Secret key (sk_test_… / sk_live_…) → dán vào ô [Secret key](#secret-secret_key) bên dưới.",
                    "Tùy chọn: copy Publishable key (pk_…) → dán vào ô [Publishable key](#secret-publishable_key) nếu frontend có nhúng Stripe.js.",
                ],
            },
            {
                "title": "Bước 2 — Đăng ký webhook endpoint",
                "steps": [
                    "Developers → Webhooks → **Add endpoint**.",
                    "Endpoint URL: copy từ box **Webhook URL** bên dưới (đã build sẵn từ `settings.BASE_URL`).",
                    "Description: tùy ý, ví dụ `AgentForge production`.",
                    "Ở phần **Select events**, chọn các event liệt kê trong Webhook box bên dưới. Khuyến nghị chọn từng cái thay vì `*` để giảm noise.",
                    "Sau khi tạo, Stripe hiện **Signing secret** (whsec_…) — copy NGAY vì chỉ hiện 1 lần. Dán vào ô [Webhook signing secret](#secret-webhook_secret) bên dưới.",
                ],
            },
            {
                "title": "Bước 3 — Bật Stripe Connect (chỉ nếu bán Hub)",
                "steps": [
                    "Settings → Connect → **Get started**. Chọn loại account = **Express** (đơn giản, Stripe hosted onboarding).",
                    "Trong Connect settings, thêm các URL: [Connect return URL](#cfg-connect_return_url) và [Connect refresh URL](#cfg-connect_refresh_url) (thường là trang `/settings/payouts` của FE).",
                    "Tác giả khi vào FE bấm Connect sẽ được redirect sang Stripe để onboard tài khoản của họ. Sau khi xong, tiền họ nhận sẽ vào tài khoản đó, không qua tài khoản platform.",
                    "Phí nền tảng [platform_fee_bps](#cfg-platform_fee_bps) trừ trực tiếp khi destination charge — buyer trả 100 USD, platform giữ 15 USD (mặc định 1500 bps), tác giả nhận 85 USD.",
                ],
            },
            {
                "title": "Bước 4 — Test & Go live",
                "steps": [
                    "Bấm **Test connection** ở footer editor để verify Stripe nhận secret key. Phải thấy 'OK' mới được.",
                    "Bật toggle **Enabled** + bấm **Save changes**. Trước đó các endpoint /checkout sẽ trả 503.",
                    "Test với card 4242 4242 4242 4242 (Visa test) — Stripe có nhiều card test khác cho lỗi insufficient_funds, 3DS, v.v.",
                    "Khi ổn rồi: tắt **Test mode** trong UI này, đổi sang sk_live_… + tạo lại webhook với endpoint mới (Stripe phân tách webhook test vs live).",
                ],
            },
        ],
        "tips": [
            "**Test mode tách biệt hoàn toàn live mode** — webhook, customers, products đều phải tạo lại. Đừng kỳ vọng dữ liệu test xuất hiện ở dashboard live.",
            "**Webhook secret bị mất**: vào endpoint trong Developers → Webhooks → **Roll secret**. Stripe sẽ accept cả secret cũ + mới trong vài giờ để không gãy production.",
            "**Connect destination charges** trừ phí từ author chứ không phải platform — `reverse_transfer=True` khi refund sẽ rút lại tiền từ tài khoản author.",
            "**Subscription metered usage** được ship qua background loop `billing_reporter` mỗi 15 phút — không phải realtime.",
        ],
        "docs": [
            ("Stripe API keys & test mode", "https://stripe.com/docs/keys"),
            ("Webhook signing & retry policy", "https://stripe.com/docs/webhooks/signatures"),
            ("Stripe Connect Express setup", "https://stripe.com/docs/connect/express-accounts"),
            ("Test card numbers", "https://stripe.com/docs/testing"),
        ],
    },
    "momo": {
        "intro": (
            "MoMo phục vụ riêng buyer Việt Nam, lock currency = **VND**. "
            "Không có Connect equivalent — platform thu tất, đối soát + "
            "thanh toán cho tác giả thực hiện thủ công ngoài hệ thống. "
            "**Subscription không support trên MoMo** — gói trả phí org "
            "vẫn phải chạy qua Stripe."
        ),
        "requirements": [
            "Tài khoản **MoMo Business** đã được duyệt (cần đăng ký kinh doanh Việt Nam hợp lệ — pháp nhân hoặc hộ kinh doanh).",
            "Domain HTTPS công khai cho IPN — MoMo không retry mạnh như Stripe, endpoint phải sẵn sàng ngay khi user thanh toán xong.",
            "Tài khoản MoMo Business test (sandbox) khác hoàn toàn account production — đăng ký riêng tại developers.momo.vn.",
        ],
        "webhook": {
            "path": "/api/webhooks/momo",
            "events": [
                "IPN — POST kết quả thanh toán (resultCode=0 ⇒ thành công)",
                "IPN — POST kết quả refund (cùng endpoint, phân biệt qua orderId)",
            ],
            "note": (
                "MoMo gửi IPN dạng JSON kèm trường `signature` (HMAC-SHA256 "
                "với secret_key của bạn). Backend tự verify chữ ký + dedupe "
                "theo `orderId` nên gửi lại 2 lần cũng không nhân đôi đơn. "
                "MoMo expect 2xx response — non-2xx họ sẽ retry 1-2 lần rồi bỏ."
            ),
        },
        "sections": [
            {
                "title": "Bước 1 — Đăng ký tài khoản MoMo Business",
                "steps": [
                    "Vào business.momo.vn → đăng ký với thông tin doanh nghiệp (MST, giấy phép kinh doanh, đại diện pháp lý).",
                    "Sandbox: vào developers.momo.vn → tạo merchant test (chỉ cần email, không cần duyệt). Lấy 3 keys test trước để dev.",
                    "Production: gửi hồ sơ + ký hợp đồng. MoMo cấp 3 keys live sau 5-15 ngày làm việc.",
                    "Kết quả: bạn có 3 keys — dán vào [Partner Code](#secret-partner_code), [Access Key](#secret-access_key), [Secret Key](#secret-secret_key) bên dưới.",
                ],
            },
            {
                "title": "Bước 2 — Cấu hình endpoint + URLs",
                "steps": [
                    "Đặt [Endpoint](#cfg-endpoint) = `https://test-payment.momo.vn` cho sandbox, `https://payment.momo.vn` cho production. Phải khớp toggle **Test mode** ở đầu form.",
                    "[IPN Notify URL](#cfg-notify_url): copy từ box **Webhook URL** bên dưới (đã build sẵn từ `settings.BASE_URL`). MoMo POST kết quả về URL này.",
                    "[Browser Return URL](#cfg-return_url) = trang FE buyer được redirect về sau khi thanh toán (vd `https://yourdomain.com/purchase/result`). Trang này nên poll `/api/purchase-status?txn_id=…` để hiện kết quả.",
                    "Đăng ký 2 URL trên trong MoMo Business dashboard ở mục **Cấu hình kỹ thuật → IPN URL / Return URL**.",
                ],
            },
            {
                "title": "Bước 3 — Test bằng sandbox",
                "steps": [
                    "Bật **Test mode** + dán keys sandbox. Bấm **Test connection** (chỉ check 3 keys có mặt — MoMo không có endpoint auth-only).",
                    "Tạo 1 template giá VND trên Hub → thử mua. MoMo sandbox có user/password test mặc định (xem developers.momo.vn).",
                    "Sau khi thanh toán xong, check log backend xem có nhận được IPN không. Nếu không nhận, debug: webhook URL có HTTPS không? Có public không? Server log có thấy POST tới không?",
                ],
            },
            {
                "title": "Bước 4 — Chuyển sang production",
                "steps": [
                    "Tắt **Test mode** trong UI, đổi Endpoint sang `https://payment.momo.vn`.",
                    "Thay 3 keys sandbox → 3 keys production (lưu ý: Partner Code production khác sandbox).",
                    "Đổi IPN Notify URL + Browser Return URL trong MoMo Business dashboard sang URL production.",
                    "Bấm **Save changes** + bật **Enabled**. Test bằng 1 đơn nhỏ (10k VND) với thẻ ATM thật để xác nhận flow.",
                ],
            },
        ],
        "tips": [
            "**Chữ ký HMAC**: MoMo sign theo thứ tự fixed (không sort alphabet) — backend đã build raw string đúng thứ tự. Đừng tự sửa hàm `_sign` trừ khi MoMo update API.",
            "**transId vs orderId**: orderId do bạn tạo (UUID), transId là MoMo cấp khi thanh toán xong. Backend lưu transId vào `provider_transaction_id` để dùng cho refund.",
            "**Refund chỉ work với transId thật** — nếu order chưa thanh toán thành công (chưa có IPN với resultCode=0) thì không thể refund.",
            "**Timezone**: MoMo trả `responseTime` theo Asia/Ho_Chi_Minh (UTC+7). Đừng so sánh với `datetime.utcnow()`.",
            "**Per-author MoMo**: nếu tác giả template tự đăng ký MoMo Business riêng và paste credentials trong Settings → Payouts, tiền sẽ vào account của họ — KHÔNG qua platform.",
        ],
        "docs": [
            ("MoMo Business portal", "https://business.momo.vn/"),
            ("MoMo Developers (sandbox + API docs)", "https://developers.momo.vn/"),
            ("MoMo Payment API v3", "https://developers.momo.vn/v3/docs/payment/"),
        ],
    },
}


def _mask(value: str) -> str:
    """Return a masked preview of a secret so the admin grid can show
    that a key is set without leaking it. Keeps the last 4 chars for
    operator identification; matches the format Stripe's dashboard uses.
    """
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


def _serialize(cfg: ProviderConfig, *, persisted: bool = True) -> dict[str, Any]:
    masked_secrets = {k: _mask(v) for k, v in cfg.secrets.items()}
    return {
        "code": cfg.code,
        "display_name": cfg.display_name,
        "kind": cfg.kind,
        "is_enabled": cfg.is_enabled,
        "is_test_mode": cfg.is_test_mode,
        "persisted": persisted,
        "secrets_preview": masked_secrets,
        "secret_keys": [
            {"key": k, "label": label, "hint": hint, "is_set": bool(cfg.secrets.get(k))}
            for k, label, hint in PROVIDER_SECRET_KEYS.get(cfg.code, [])
        ],
        "config": cfg.config,
        "config_keys": [
            {"key": k, "label": label, "hint": hint}
            for k, label, hint in PROVIDER_CONFIG_KEYS.get(cfg.code, [])
        ],
        "guide": _guide_for(cfg.code),
        "last_tested_at": cfg.last_tested_at.isoformat() if cfg.last_tested_at else None,
        "last_test_result": cfg.last_test_result,
    }


def _guide_for(code: str) -> dict[str, Any] | None:
    """Return the guide for ``code`` with webhook URL fully resolved
    using ``settings.BASE_URL``. Splitting this out keeps PROVIDER_GUIDES
    declarative — the env lookup happens at request time so a runtime
    BASE_URL change propagates without a server restart."""
    guide = PROVIDER_GUIDES.get(code)
    if guide is None:
        return None
    webhook = guide.get("webhook")
    if not webhook or not webhook.get("path"):
        return guide
    base = settings.BASE_URL.rstrip("/")
    return {
        **guide,
        "webhook": {
            **webhook,
            "url": f"{base}{webhook['path']}",
        },
    }


def _placeholder(code: str) -> ProviderConfig:
    """Synthesise an empty ``ProviderConfig`` for a provider that has a
    class in code but no DB row yet. Lets the admin form render with
    sensible defaults — saving the form upserts the row."""
    defaults = _PROVIDER_DEFAULTS.get(code, {"display_name": code.title(), "kind": "both"})
    return ProviderConfig(
        code=code,
        display_name=defaults["display_name"],
        kind=defaults["kind"],
        is_enabled=False,
        is_test_mode=True,
        secrets={},
        config={},
    )


async def list_for_admin() -> list[dict[str, Any]]:
    """All providers — persisted DB rows merged with the in-code
    registry so admins on a fresh deploy still see Stripe/MoMo and can
    fill them in from the UI (no CLI required)."""
    rows = await list_provider_configs()
    by_code = {r.code: r for r in rows}
    out: list[dict[str, Any]] = [_serialize(r, persisted=True) for r in rows]
    for code in PROVIDER_SECRET_KEYS:
        if code not in by_code:
            out.append(_serialize(_placeholder(code), persisted=False))
    return out


async def get_for_admin(code: str) -> dict[str, Any] | None:
    cfg = await get_provider_config(code)
    if cfg is not None:
        return _serialize(cfg, persisted=True)
    # No DB row yet, but the provider is known to the registry — return
    # an empty editor scaffold instead of 404 so deep-links work.
    if code in PROVIDER_SECRET_KEYS:
        return _serialize(_placeholder(code), persisted=False)
    return None


async def upsert_from_admin(
    code: str,
    *,
    display_name: str,
    kind: str,
    is_enabled: bool,
    is_test_mode: bool,
    secrets: dict[str, str] | None,
    config: dict[str, Any] | None,
    description: str | None,
    actor_user_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Save admin edits. ``secrets=None`` preserves existing secrets so
    the admin can edit non-secret config without re-entering the key
    (FE sends None for unchanged secrets)."""
    result = await upsert_provider_config(
        code,
        display_name=display_name,
        kind=kind,
        is_enabled=is_enabled,
        is_test_mode=is_test_mode,
        secrets=secrets,
        config=config,
        description=description,
        actor_user_id=actor_user_id,
    )
    return _serialize(result)


async def delete_from_admin(code: str) -> bool:
    return await delete_provider_config(code)


async def run_test_connection(code: str) -> dict[str, Any]:
    ok, msg = await test_provider_connection(code)
    return {"ok": ok, "message": msg}


__all__ = [
    "PROVIDER_CONFIG_KEYS",
    "PROVIDER_SECRET_KEYS",
    "delete_from_admin",
    "get_for_admin",
    "list_for_admin",
    "run_test_connection",
    "upsert_from_admin",
]
