import type { ComponentDefinition } from "@/client"

/**
 * Propuesta de archivos y hojas por el nombre que el usuario da a cada componente.
 *
 * Se comparan palabras completas, sin mayúsculas, acentos ni separadores habituales:
 * «BASE» coincide con `20240508_BASE_RCP31.stp` y con `DR(base)`, pero no con `BASE2`.
 * Un nombre de varias palabras debe aparecer seguido. Si coinciden varios componentes,
 * o ninguno, no hay propuesta: la fuente queda sin asignar.
 */
export function words(text: string): string[] {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
}

export function nameMatches(text: string, name: string): boolean {
  const target = words(name)
  const found = words(text)
  if (!target.length) return false
  for (let start = 0; start + target.length <= found.length; start++)
    if (target.every((word, i) => found[start + i] === word)) return true
  return false
}

/** Clave del único componente cuyo nombre aparece en el texto, si lo hay. */
export function proposedComponent(
  text: string,
  components: Pick<ComponentDefinition, "key" | "name">[],
): string | undefined {
  const matches = components.filter((c) => nameMatches(text, c.name))
  return matches.length === 1 ? matches[0].key : undefined
}

/** Nombre del archivo sin carpeta ni extensión: lo que describe su contenido. */
export function fileStem(path: string): string {
  const name = path.split("/").pop() ?? path
  const dot = name.lastIndexOf(".")
  return dot > 0 ? name.slice(0, dot) : name
}

const WORKBOOK = /\.(xls|xlsx|xlsm)$/i

/**
 * Un libro Excel puede tener hojas de varios componentes: se proponen sus hojas,
 * nunca el libro entero por su nombre.
 */
export function proposesWholeFile(path: string): boolean {
  return !WORKBOOK.test(path)
}
