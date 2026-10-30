const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * "Oct 20, 2026", as the designs write dates. A date with no time is that
 * calendar day wherever the reader is; a timestamp is shown in their own zone.
 */
export function formatDate(value: string, locale = "en-US"): string {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: DATE_ONLY.test(value) ? "UTC" : undefined,
  }).format(new Date(value));
}
