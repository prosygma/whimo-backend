# Languages

The languages offered in the web app and the mobile apps are managed in the admin,
under **Languages**. Each installation picks its own. For example, an installation in
Cameroon offers French and English, and one in India could offer Hindi and English.

The apps ship strings for English, French and Spanish. Every language, shipped or not,
can be:

- **enabled or disabled**: a disabled language disappears from every language picker. Users
  who had chosen it move to the default language;
- **the default**: the language used when the user's own language is not offered (only one);
- **ordered** (Position): the order in the language pickers, lowest first;
- **translated or corrected** by uploading a file, without a new release of the apps.

## Remove a language

In **Languages**, untick **Is enabled** on its row and save. You can't disable the default
language: make another language the default first (the **Make default** button on its page).

## Add a language

1. In **Languages**, click **Download English template**. You get
   `translations-template-en.json`, which has every string of every app:

   ```json
   {
     "web":     { "common": { "email": "Email", ... }, "login": { ... }, ... },
     "android": { "email": "Email", ... },
     "ios":     { "general.keyboard.toolbar.done": "Done", ... },
     "api":     { "Your verification code is: %s": "Your verification code is: %s", ... }
   }
   ```

   - `web` is the web app (grouped by page), `android` and `ios` the mobile apps, and `api`
     the messages of the server (SMS, e-mails, errors).
   - The same text can appear in several sections: translate it in each.
2. Translate the **values** (right of the colon). Keep:
   - the **keys** (left of the colon) as they are;
   - the **placeholders**: `%s`, `%1$s`, `%d`, `%@`, `%(app_name)s`, `{{count}}`, and tags
     like `<btn>…</btn>` or `<0>…</0>`. The apps put a value or a link there.
3. Click **Add language** and fill in:
   - **Code**: the ISO 639 code, for example `hi` for Hindi. It can't be changed later.
   - **Name**: the name in the language itself, for example `हिन्दी`, as shown in the pickers.
   - **English name** (optional), and **Flag** (optional emoji, for example 🇮🇳).
4. Choose the file in **Translations file** and save.

The admin then says how many strings it stored. If the file has mistakes, nothing is stored
and each mistake is listed (unknown key, missing placeholder, invalid JSON…).

You don't have to translate everything at once. A string left in English, or left empty,
is shown in English, and **Translated** shows the progress (for example `812 / 1129 (72%)`).
Upload the file again as the work goes on.

## Correct some strings

1. Open the language and click **Download translations**: every string as the apps show it
   now (strings not translated yet come in English).
2. Change what you need, then upload the file in **Translations file** and save.

Only the strings that differ from the apps' own text are stored. The rest of the file changes
nothing. A string already uploaded and missing from a new file is kept.

## When the change is visible

- Enabling, disabling or reordering: within a few minutes. The web app picks it up when the
  page is reloaded, and the mobile apps at their next start.
- Uploaded strings: the same way. The apps download them once and keep them for offline use.

## Limits

- Scripts written right to left (Arabic, Urdu…) show their words correctly, but the screens
  are still laid out left to right.
- Dates keep the apps' current format.
- The terms of use and the privacy policy are not part of the file.

## For developers

- `whimo/languages/catalog/<code>.json` holds the strings the apps ship. English is the
  template and defines the valid keys. When an app adds or renames strings, regenerate it:

  ```bash
  python scripts/export_strings.py \
      --web ../whimo/public/locales \
      --android ../whimo-android/app/src/main/res \
      --ios ../whimo-ios/Packages/Resources/Sources/Resources/Localization
  ```

  Pass a second `--android` with a product flavor's `res` folder to include its overrides.
- Public API used by the apps:
  - `GET /api/v1/languages/`: the enabled languages, the default and their versions;
  - `GET /api/v1/languages/<code>/<web|android|ios>/`: the strings uploaded for one platform.
    The apps put them on top of their own strings.
- `LanguageMiddleware` replaces Django's `LocaleMiddleware`: the request language is the
  best enabled match of `Accept-Language`, else the default one. The `api` strings uploaded
  for a language are added to Django's translations.
