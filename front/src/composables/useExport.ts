import { ref } from 'vue'

/**
 * Excel'ga chiqarish tugmasi holati.
 *
 * Uch sahifada bir xil takrorlanadi: bosilganda kutish, xato bo'lsa
 * ko'rsatish. Fayl katta bo'lsa server bir necha soniya tayyorlaydi —
 * shuning uchun tugma shu vaqtda bloklanadi, aks holda foydalanuvchi
 * uni bir necha marta bosib, serverga bir xil so'rovni takrorlardi.
 */
export function useExport(request: () => Promise<void>) {
  const exporting = ref(false)
  const exportError = ref('')

  async function onExport() {
    if (exporting.value) return

    exportError.value = ''
    exporting.value = true

    try {
      await request()
    } catch {
      // Server javobi `blob` sifatida keladi, shuning uchun xato matnini
      // o'qish ishonchsiz — umumiy xabar beramiz.
      exportError.value = 'Faylni tayyorlab bo‘lmadi. Qaytadan urinib ko‘ring.'
    } finally {
      exporting.value = false
    }
  }

  return { exporting, exportError, onExport }
}
