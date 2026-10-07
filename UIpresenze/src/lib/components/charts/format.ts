/** Formattazioni condivise: un solo posto per ore, euro, percentuali e date. */

const IT = 'it-IT';

export function fmtHours(seconds: number) {
  const hours = seconds / 3600;
  const rounded = Math.round(hours * 10) / 10;
  return Number.isInteger(rounded)
    ? `${rounded.toLocaleString(IT)} h`
    : `${rounded.toLocaleString(IT, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} h`;
}

/** Ore per gli assi: niente decimali, serve solo la scala. */
export function fmtHoursAxis(seconds: number) {
  return `${Math.round(seconds / 3600).toLocaleString(IT)} h`;
}

export function fmtPercent(value: number, decimals = 1) {
  return `${value.toLocaleString(IT, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })}%`;
}

export function fmtEuro(value: number) {
  return value.toLocaleString(IT, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
    // Senza, l'italiano lascia i quattro cifre senza punto: "5701 €" accanto a "16.554 €".
    useGrouping: 'always'
  });
}

/** Euro abbreviati per le etichette degli assi. */
export function fmtEuroAxis(value: number) {
  const abs = Math.abs(value);
  const short = (amount: number) => amount.toLocaleString(IT, { maximumFractionDigits: 1 });
  if (abs >= 1_000_000) return `${short(value / 1_000_000)} M€`;
  if (abs >= 1_000) return `${short(value / 1_000)} k€`;
  return `${Math.round(value)} €`;
}

/** Tariffa oraria effettiva. */
export function fmtRate(value: number) {
  return `${value.toLocaleString(IT, { maximumFractionDigits: 0 })} €/h`;
}

export function fmtInt(value: number) {
  return Math.round(value).toLocaleString(IT);
}

export function fmtDays(days: number) {
  const rounded = Math.round(days);
  return `${rounded.toLocaleString(IT)} ${Math.abs(rounded) === 1 ? 'giorno' : 'giorni'}`;
}

/** Etichetta breve di un mese: "set 26". */
export function fmtMonth(date: Date) {
  return date.toLocaleDateString(IT, { month: 'short', year: '2-digit' });
}

/** Solo il mese, quando l'anno e' gia' nel titolo: "set". */
export function fmtMonthName(date: Date) {
  return date.toLocaleDateString(IT, { month: 'short' });
}

/** Etichetta breve di un giorno: "21 set". */
export function fmtDay(date: Date) {
  return date.toLocaleDateString(IT, { day: 'numeric', month: 'short' });
}
