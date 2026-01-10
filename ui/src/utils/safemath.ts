/**
 * Safe math helpers to avoid NaN/Infinity in UI.
 */

export const safeDivide = (numerator: number, denominator: number, fallback = 0) => {
  if (denominator === 0 || !Number.isFinite(numerator) || !Number.isFinite(denominator)) {
    return fallback;
  }
  const result = numerator / denominator;
  return Number.isFinite(result) ? result : fallback;
};

export const safePercent = (value: number, total: number, fallback = 0) => {
  return safeDivide(value, total, fallback) * 100;
};

export const safeToFixed = (
  value: number | null | undefined,
  decimals = 2,
  fallback = 'N/A'
) => {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return fallback;
  }
  return value.toFixed(decimals);
};

export const safeAverage = (values: number[]) => {
  if (!Array.isArray(values) || values.length === 0) return 0;
  const validValues = values.filter(Number.isFinite);
  if (validValues.length === 0) return 0;
  return validValues.reduce((sum, value) => sum + value, 0) / validValues.length;
};
