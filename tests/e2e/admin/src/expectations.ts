/**
 * Pages that are *correctly* not 200, so the crawl asserts the expectation
 * instead of reporting a false failure.
 *
 * `ReadOnlyAdminMixin` (whimo/contrib/utils.py) overrides has_add/change/delete
 * but leaves has_view alone: change pages render read-only, add/ and delete/
 * raise PermissionDenied. `UserAdmin.has_delete_permission` returns False too.
 */
export const READ_ONLY_MODELS = ['db.transaction', 'db.balance', 'db.notification'];

/** Models whose delete view is denied (read-only ones, plus User). */
export const NO_DELETE_MODELS = [...READ_ONLY_MODELS, 'db.user'];

/**
 * Single-row models: has_add_permission is true only while no row exists, so
 * add/ answers 200 on an empty database and 403 once the row is saved.
 */
export const SINGLETON_MODELS = ['db.whatsappsettings'];

export function expectedAddStatus(label: string): number[] {
  if (SINGLETON_MODELS.includes(label.toLowerCase())) return [200, 403];
  return READ_ONLY_MODELS.includes(label.toLowerCase()) ? [403] : [200];
}

export function isReadOnly(label: string): boolean {
  return READ_ONLY_MODELS.includes(label.toLowerCase());
}

/** Never navigate to these: logout kills the shared storageState. */
export const SKIP_URL_PATTERNS = [
  /\/admin\/logout\//,
  /\/admin\/login\//,
  /\/delete\/$/,
  /\/admin\/jsi18n\//,
];

/**
 * Responses sent as attachments. `page.goto` aborts on Content-Disposition,
 * so these are fetched with the request context instead.
 */
export const DOWNLOAD_URL_PATTERNS = [
  /\/download_geojson\/$/,
  /\/export\/$/,
  // Languages admin: the English template and each language's translations (JSON).
  /\/admin\/languages\/language\/download-template\/$/,
  /\/admin\/languages\/language\/[^/]+\/download\/$/,
];

export function isDownloadUrl(url: string): boolean {
  return DOWNLOAD_URL_PATTERNS.some((pattern) => pattern.test(url));
}

export function shouldSkipUrl(url: string): boolean {
  return SKIP_URL_PATTERNS.some((pattern) => pattern.test(url));
}
