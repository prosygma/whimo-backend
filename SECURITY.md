# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Report it privately through GitHub instead: open the repository's **Security** tab and choose
**Report a vulnerability**. Include what you found, how to reproduce it, and what an attacker
could do with it. We answer within a few working days.

If the problem is also present in the original WHIMO code, say so: we will coordinate with the
European Forest Institute so that every WHIMO deployment gets the fix.

## What to report

- Ways to read or change data that belongs to another user or organisation.
- Authentication, verification code, or session flaws.
- Secrets or personal data exposed by the apps, the API, or this repository.

## Handling secrets and personal data

- Never commit credentials, signing keys, `google-services.json`, `GoogleService-Info*.plist`,
  `.env` files with real values, or database dumps. Use the `*.example` / `*.sample` files.
- Never put real personal data in code, tests, fixtures, screenshots, or issues. This includes
  farmer card contents (a CICC card identifies a farmer), phone numbers, e-mail addresses, and
  plot coordinates. Use made-up values shaped like the real ones.
