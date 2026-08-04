export function reconcileIRPFYear(
  currentYear: number,
  availableYears: readonly number[] | undefined,
  fallbackYear: number,
): number {
  if (!availableYears || availableYears.length === 0) {
    return fallbackYear
  }

  if (availableYears.includes(currentYear)) {
    return currentYear
  }

  return availableYears[0]
}
