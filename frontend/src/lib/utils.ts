import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Numeric-aware, case-insensitive name ordering ("Crew 2" < "Crew 10"). The API
// returns rows in plain lexicographic order; every user-facing list re-sorts
// through this collator.
export const nameCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
})

export function sortByName<T>(items: readonly T[], name: (item: T) => string): T[] {
  return [...items].sort((a, b) => nameCollator.compare(name(a), name(b)))
}

// ISO "YYYY-MM-DD HH:mm" in local time — dates render in ISO everywhere.
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
