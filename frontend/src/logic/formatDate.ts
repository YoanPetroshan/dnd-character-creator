/** Locale date-time text; some ICU builds print the Bulgarian hour suffix twice. */
const DOUBLE_SUFFIX = /( ч\.) ч\./g;

export function formatDateTime(value: string | number | Date, locale: string): string {
  return new Date(value).toLocaleString(locale).replace(DOUBLE_SUFFIX, "$1");
}
