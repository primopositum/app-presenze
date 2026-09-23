/**
 * Mattoncini comuni a tutti i filtri: confronti su liste, intervalli, date e
 * testo. Non conoscono nessuna schermata; la logica di ciascuna sta nella sua
 * cartella (`jiraHistory/`, `contratti/`, ...).
 */
import type { DateSpan, NumberRange } from './types';

/** Lista vuota = nessun filtro. */
export function inList(list: string[], value: string) {
  return list.length === 0 || list.includes(value);
}

/** Estremi inclusi; un estremo vuoto non limita. `scale` converte l'unita' del pannello. */
export function inRange(range: NumberRange, value: number, scale = 1) {
  if (range.min !== null && value < range.min * scale) return false;
  if (range.max !== null && value > range.max * scale) return false;
  return true;
}

/** Confronto su YYYY-MM-DD: l'ordine lessicale e' anche quello cronologico. */
export function inDates(span: DateSpan, day: string | null | undefined) {
  if (!span.from && !span.to) return true;
  const value = String(day || '').slice(0, 10);
  if (!value) return false;
  if (span.from && value < span.from) return false;
  if (span.to && value > span.to) return false;
  return true;
}

export function textMatches(needle: string, ...haystack: (string | null | undefined)[]) {
  const query = needle.trim().toLowerCase();
  if (!query) return true;
  return haystack.some((item) => String(item || '').toLowerCase().includes(query));
}

/** Espressione regolare scritta nel pannello; null se vuota o non valida. */
export function compileRegex(pattern: string): RegExp | null {
  const source = pattern.trim();
  if (!source) return null;
  try {
    return new RegExp(source, 'i');
  } catch {
    return null;
  }
}

export function regexError(pattern: string): string {
  const source = pattern.trim();
  if (!source) return '';
  try {
    new RegExp(source, 'i');
    return '';
  } catch (cause) {
    return cause instanceof Error ? cause.message : 'Espressione non valida';
  }
}

/** "ABC-1, abc-2 ABC-3" -> set in maiuscolo. */
export function keyList(text: string) {
  return new Set(
    text
      .split(/[\s,;]+/)
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean)
  );
}

/** Giorno della settimana di una data YYYY-MM-DD: 0 = lunedi', come nei grafici. */
export function weekdayOf(day: string) {
  const match = String(day || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return -1;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return (date.getDay() + 6) % 7;
}
