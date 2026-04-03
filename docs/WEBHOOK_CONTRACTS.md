# Webhook Payload Contracts

This document defines the exact JSON schemas for the two external webhook integrations.

---

## 1. AI Content Generation Webhook

**Direction:** PolitmaTrader → Your AI endpoint (outbound)

**Trigger:** Called during asset generation when `AI_WEBHOOK_URL` is configured.

### Request

```
POST {AI_WEBHOOK_URL}
Content-Type: application/json
Authorization: Bearer {AI_WEBHOOK_TOKEN}
```

```json
{
  "brand_name": "POLITMATRADER",
  "brand_domain": "https://politmatrader.com",
  "coupon_code": "EASTER20",
  "coupon_description": "20% OFF all challenges for the month of April",
  "pillar": "education",
  "topic": "Risk management before profit targets",
  "angle": "myth-busting",
  "platform": "instagram",
  "cta_primary": "Start Challenge Now"
}
```

| Field               | Type   | Description                                       |
|---------------------|--------|---------------------------------------------------|
| brand_name          | string | Brand name for copy                               |
| brand_domain        | string | URL to link to                                    |
| coupon_code         | string | Active promo code                                 |
| coupon_description  | string | Human-readable promo description                  |
| pillar              | string | One of: education, authority, promotion, lifestyle |
| topic               | string | Content topic from topic bank                     |
| angle               | string | Creative angle (myth-busting, step-by-step, etc.) |
| platform            | string | Target platform (instagram, x, youtube, etc.)     |
| cta_primary         | string | Call-to-action text                               |

### Expected Response (200 OK)

```json
{
  "hook": "Most traders fail because they skip this one rule.",
  "body": "Risk management separates funded traders from gamblers. Before chasing profit targets, define your max drawdown...",
  "cta": "Start Challenge Now at https://politmatrader.com",
  "hashtags": ["#PolitmaTrader", "#FundedTrader", "#RiskManagement"],
  "visual_brief": "Premium black-and-gold Instagram reel. Bold typography overlay: 'The Rule Most Traders Break'. Dark background, gold accent lines."
}
```

| Field        | Type     | Required | Description                        |
|--------------|----------|----------|------------------------------------|
| hook         | string   | Yes      | Attention-grabbing opening line    |
| body         | string   | Yes      | Main post content                  |
| cta          | string   | Yes      | Call to action with link           |
| hashtags     | string[] | Yes      | Up to 8 hashtags                   |
| visual_brief | string   | Yes      | Creative direction for designers   |

### Error Handling

If the webhook returns a non-200 status, times out (30s), or is missing any required field, the system silently falls back to the built-in rule-based generator. No content is lost.

---

## 2. Social Publishing Webhook

**Direction:** PolitmaTrader → Your publishing tool (outbound)

**Trigger:** Called during `POST /distribution/publish` when `PUBLISH_WEBHOOK_URL` is configured.

### Request

```
POST {PUBLISH_WEBHOOK_URL}
Content-Type: application/json
Authorization: Bearer {PUBLISH_WEBHOOK_TOKEN}
```

```json
{
  "asset_id": "2025-04-15-instagram-reel-a3f8c201",
  "platform": "instagram",
  "format": "reel",
  "hook": "April only: use EASTER20 for 20% OFF all challenges.",
  "body": "This month only, POLITMATRADER is giving traders a reason to act...",
  "cta": "Use EASTER20 now — Start Challenge Now: https://politmatrader.com",
  "hashtags": "[\"#PolitmaTrader\", \"#FundedTrader\", \"#EASTER20\"]",
  "visual_brief": "Create a premium black-and-gold Instagram creative...",
  "scheduled_time": "2025-04-15T13:00:00+00:00"
}
```

| Field          | Type   | Description                                     |
|----------------|--------|-------------------------------------------------|
| asset_id       | string | Unique asset identifier                         |
| platform       | string | Target social platform                          |
| format         | string | Content format (reel, post, thread, etc.)       |
| hook           | string | Opening line / headline                         |
| body           | string | Full post body                                  |
| cta            | string | Call to action text                             |
| hashtags       | string | JSON-encoded array of hashtag strings           |
| visual_brief   | string | Creative direction for visual assets            |
| scheduled_time | string | ISO 8601 datetime when the post should go live  |

### Expected Response (200 OK)

```json
{
  "external_post_id": "buffer-abc123def456",
  "status": "published",
  "message": "Post scheduled successfully"
}
```

| Field            | Type   | Required | Description                          |
|------------------|--------|----------|--------------------------------------|
| external_post_id | string | Yes      | ID from the publishing platform      |
| status           | string | No       | "published" or "scheduled"           |
| message          | string | No       | Human-readable status message        |

### Error Handling

- HTTP 4xx/5xx: The queue item enters retry state (up to 3 retries).
- Timeout (30s): Treated as a failure, enters retry.
- After 3 failed retries: Item is marked `failed`, asset status becomes `error`.
- No webhook configured: Publish is simulated with a generated ID — the system remains fully functional without external integrations.

---

## Inbound Webhook Security (for your endpoints receiving data from PolitmaTrader)

If you build an endpoint that *receives* data from PolitmaTrader (e.g., analytics callbacks), verify the signature:

```
X-Webhook-Signature: <HMAC-SHA256 hex digest of request body using WEBHOOK_SECRET>
```

Verification pseudocode:
```python
import hmac, hashlib

expected = hmac.new(
    webhook_secret.encode(),
    request_body,
    hashlib.sha256
).hexdigest()

is_valid = hmac.compare_digest(expected, request.headers["X-Webhook-Signature"])
```
