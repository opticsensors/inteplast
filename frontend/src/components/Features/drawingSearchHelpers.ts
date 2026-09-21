export const normalizeCota = (text: string) =>
  text
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "")
    .replace(/^N?0*(\d+)/, "N$1")
export const matchesCota = (label: string, query: string, children: boolean) =>
  label === query || (children && label.startsWith(`${query}.`))

/** Search suggestions accept unfinished numbers, including subdimension prefixes. */
export const matchesCotaPrefix = (label: string, query: string) =>
  normalizeCota(label).startsWith(normalizeCota(query))
