import type { SourceSheet } from "@/client"

export type CellPosition = { sheet: number; row: number; column?: number }

export function columnLabel(index: number): string {
  let value = index + 1
  let result = ""
  while (value) {
    result = String.fromCharCode(65 + ((value - 1) % 26)) + result
    value = Math.floor((value - 1) / 26)
  }
  return result
}

const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
const numeric = (value: string) =>
  value.trim() ? Number(value.trim().replace(",", ".")) : Number.NaN

/** Resolve saved locators, including the pilot's repeated CMM block identities. */
export function sourcePosition(
  sheets: SourceSheet[],
  locator: string,
  cavity?: string,
  value?: string,
): CellPosition | undefined {
  const cell = /^(?:'(.+)'|(.+))!\$?([A-Z]+)\$?(\d+)$/i.exec(locator.trim())
  if (cell) {
    const sheet = sheets.findIndex((item) => item.name === (cell[1] ?? cell[2]))
    let column = 0
    for (const letter of cell[3].toUpperCase())
      column = column * 26 + letter.charCodeAt(0) - 64
    const row = Number(cell[4]) - 1
    return sheet >= 0 && row >= 0 && row < sheets[sheet].rows.length
      ? { sheet, row, column: column - 1 }
      : undefined
  }
  const grid = sheets[0]?.rows
  if (!grid) return undefined
  const line = /^L[ií]nea\s+(\d+)\b/i.exec(locator)
  let row = line ? Number(line[1]) - 1 : -1
  const block = /^(.*?) · aparición (\d+) · fila (\d+)(?: · CMM .*)?$/.exec(
    locator,
  )
  if (block) {
    let occurrence = 0
    let index = 0
    let inBlock = false
    row = grid.findIndex((cells) => {
      const text = cells.join(";").replace(/^[;\s]+|[;\s]+$/g, "")
      if (!text || text.startsWith("****") || text.startsWith("////"))
        return false
      if (cells.length < 8 || !cells[1]?.trim()) {
        inBlock = text === block[1]
        if (inBlock) occurrence++
        index = 0
        return false
      }
      index++
      return (
        inBlock && occurrence === Number(block[2]) && index === Number(block[3])
      )
    })
  }
  if (row < 0 || row >= grid.length) return undefined
  let columns: number[] = []
  for (let r = row - 1; r >= 0; r--) {
    const header = grid[r].flatMap((v, c) =>
      /^c(?:av(?:ity)?\.?\s*)?\d+(?:[.\s_-].*)?$/i.test(v.trim()) ? [c] : [],
    )
    if (header.length) {
      columns = header.filter((c) => {
        const match = /^c(?:av(?:ity)?\.?\s*)?(\d+)/i.exec(grid[r][c].trim())
        return (
          !cavity || (match && `c${Number(match[1])}` === cavity.toLowerCase())
        )
      })
      break
    }
  }
  // Individual CMM exports store the observed value in column G.
  if (!columns.length && grid[row].length >= 8) columns = [6]
  if (value !== undefined)
    columns = columns.filter(
      (c) => Math.abs(numeric(grid[row][c] ?? "") - numeric(value)) < 1e-9,
    )
  return {
    sheet: 0,
    row,
    column: columns.length === 1 ? columns[0] : undefined,
  }
}

export function searchCells(
  sheets: SourceSheet[],
  query: string,
): CellPosition[] {
  const needle = normalize(query.trim())
  if (!needle) return []
  const address = sourcePosition(sheets, query)
  if (address) return [address]
  const found: CellPosition[] = []
  for (const [sheet, item] of sheets.entries()) {
    for (const [row, cells] of item.rows.entries()) {
      for (const [column, value] of cells.entries()) {
        if (normalize(value).includes(needle))
          found.push({ sheet, row, column })
        if (found.length >= 1000) return found
      }
    }
  }
  return found
}
