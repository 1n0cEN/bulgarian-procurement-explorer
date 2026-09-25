// Fixed official conversion rate, Council Regulation (EU) 2025/1409.
// Integer arithmetic prevents binary floating-point errors, even for large totals.
export function bgnToEur(value: string): string {
  if (!/^\d+(\.\d+)?$/.test(value))
    throw new Error("Invalid nonnegative amount");
  const [whole, fraction = ""] = value.split(".");
  const units = BigInt(whole + fraction);
  const denominator = 195583n * 10n ** BigInt(fraction.length);
  const numerator = units * 10000000n; // value / 1.95583 expressed in cents
  const cents = (numerator * 2n + denominator) / (2n * denominator);
  return `${cents / 100n}.${(cents % 100n).toString().padStart(2, "0")}`;
}

export function sourceMoney(value: string, currency: string): string {
  const [whole, fraction = ""] = value.split(".");
  return `${BigInt(whole).toLocaleString("en-GB")}${fraction && /[1-9]/.test(fraction) ? "." + fraction.replace(/0+$/, "").padEnd(2, "0") : ""} ${currency}`;
}

export function displayMoney(
  value: string | null,
  currency: string | null,
): string {
  if (value === null || !currency) return "Not reported";
  const original = sourceMoney(value, currency);
  return currency === "BGN"
    ? `${sourceMoney(bgnToEur(value), "EUR")} equivalent (source: ${original})`
    : original;
}
