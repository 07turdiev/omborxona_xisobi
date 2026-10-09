/**
 * Ombordagi shkafning kataklari.
 *
 * Ustunlar harf (A, B, C...), qatorlar raqam. Katak nomi shu ikkisidan
 * yig'iladi — `B2`. Serverdagi ro'yxat bilan bir xil bo'lishi kerak:
 * `back/apps/inventory/storage.py`.
 */

const LETTERS = 'ABCDEFGHIJKL'

/** Shkafdagi hamma katak, chapdan o'ngga va yuqoridan pastga. */
export function cellNames(columns: number, rows: number): string[] {
  const names: string[] = []

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns && column < LETTERS.length; column += 1) {
      names.push(`${LETTERS[column]}${row + 1}`)
    }
  }

  return names
}
