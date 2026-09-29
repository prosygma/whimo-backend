# Verification codes by WhatsApp

Phone verification and password-reset codes can be delivered through the
**Meta WhatsApp Cloud API** instead of SMS. The feature is off by default.
An administrator configures it in the admin, under **WhatsApp**.

When it is enabled and complete, *all* phone codes go through WhatsApp and SMS
is no longer used for them. E-mail codes and invite SMS are unchanged.

## What to prepare in Meta

1. **A WhatsApp Business account and a sender number** (Meta Business Suite ›
   WhatsApp Manager). Meta's free test number is enough to try the feature.
2. **Phone number ID**: WhatsApp Manager › API Setup, below the sender number.
   This is *not* the phone number itself.
3. **A permanent access token**:
   1. Business Settings › Users › System users: create a system user.
   2. Assign it the WhatsApp account.
   3. Generate a token with the `whatsapp_business_messaging` permission.

   Temporary tokens from API Setup expire after 24 h.
4. **An authentication template**:
   1. WhatsApp Manager › Message templates › Create, category **Authentication**.
   2. Choose **Copy code** as the button type.
   3. Add one language per app language (for example English `en_US`, French
      `fr`, Spanish `es`).
   4. Wait for approval.

## Fill in the admin

| Field | Value |
|---|---|
| Api version | Graph API version, for example `v21.0` |
| Phone number id | from step 2 |
| Access token | from step 3 (write-only: it is never shown again; leave empty to keep it) |
| Template name | name of the template from step 4 |
| Template languages | app language → template language, e.g. `{"en-us": "en_US", "fr-fr": "fr", "es-es": "es"}` |
| Test phone number | a WhatsApp number with country code, to receive the test code |

Then:
1. Save.
2. Click **Send test message**. Meta's answer (message id or error) is shown and
   kept in *Last test status*.
3. Tick **Is enabled** and save. Enabling is refused while a required field is
   empty.

## Behaviour

- **Language:** the code is sent in the language of the request. Languages
  missing from the map fall back to the first entry.
- **Retries:** network errors and Meta 5xx errors are retried (3 times, with
  backoff). 4xx errors (bad token, template or number) are logged and not
  retried.
- **API response:** `POST /auth/otp/send/` and `/auth/otp/password-reset/send/`
  return `channel` (`email`, `sms` or `whatsapp`), so the apps can tell users
  where to look.
