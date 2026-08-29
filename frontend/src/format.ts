export function formatEuro(v?: number | null): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return "€ " + v.toFixed(2).replace(".", ",");
}

export function formatEuroPlain(v?: number | null): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "0,00";
  return v.toFixed(2).replace(".", ",");
}

// Relative date label in Italian for grouping history.
export function dateLabel(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((startOf(now) - startOf(d)) / 86400000);
  if (diffDays <= 0) return "Oggi";
  if (diffDays === 1) return "Ieri";
  if (diffDays < 7) return `${diffDays} giorni fa`;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "long", year: "numeric" });
}

export function quoteId(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
}
