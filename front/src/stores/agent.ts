import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as agentApi from '@/api/agent'
import type { AgentHealth, LabelItem } from '@/api/agent'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Sale } from '@/types'

/**
 * Chop etish agentining holati.
 *
 * Agent ixtiyoriy: yo'q bo'lsa hamma narsa avvalgidek brauzer orqali
 * chop etiladi. Shuning uchun `printReceipt`/`printLabels` `false`
 * qaytarsa, chaqiruvchi brauzer yo'liga o'tadi.
 */
export const useAgentStore = defineStore('agent', () => {
  const health = ref<AgentHealth | null>(null)
  const checked = ref(false)

  const available = computed(() => health.value !== null)
  const version = computed(() => health.value?.version ?? '')
  const printers = computed(() => health.value?.printers ?? [])

  /**
   * Agent bormi.
   *
   * Bu chaqiruv chop etish yo'lida EMAS: u faqat Sozlamalardagi
   * ko'rinish va xabar matni uchun. Shuning uchun uni shoshiltirish
   * shart emas.
   */
  async function probe(fresh = false): Promise<boolean> {
    health.value = await agentApi.health(fresh)
    checked.value = true

    return available.value
  }

  /**
   * Agentga yuborishga urinadi.
   *
   * Agent bor, lekin printer javob bermasa — xabar ko'rsatiladi va
   * `false` qaytadi: chek yo'qolmasin, brauzer orqali chiqsin.
   */
  async function trySend(send: () => Promise<void>, done: string): Promise<boolean> {
    const toast = useToastStore()

    // Chop etish oldindan tekshiruvga BOG'LANMAYDI.
    //
    // Oldin shunday edi: avval `/health` so'raladi, javob 300 ms da
    // kelmasa agent «yo'q» deb hisoblanardi. Printer o'chirilgan
    // bo'lsa agentning javobi aynan shu chegara atrofida bo'lardi
    // (o'lchangan: 260-390 ms), ya'ni chek tasodifan brauzer oynasiga
    // tushardi. Sahifa qayta ochilganda esa holat noldan boshlanib,
    // xato butun seansga yopishib qolardi.
    //
    // Endi to'g'ridan-to'g'ri yuboramiz: agent yo'q bo'lsa 127.0.0.1
    // ga ulanish darhol rad etiladi, ya'ni kutish ham yo'q.
    try {
      await send()
      toast.show(done)

      // Birinchi muvaffaqiyatli chop etish holatni ham tiklaydi
      if (!available.value) void probe()

      return true
    } catch (error) {
      // Agent umuman o'rnatilmagan bo'lsa jim qolamiz: u ixtiyoriy va
      // har sotuvda qizil xabar chiqarib turish keraksiz. Agentni
      // ko'rgan bo'lsak — sababini aytamiz.
      const seen = available.value

      // Kutmaymiz: brauzer oynasi darhol ochilishi kerak
      void probe()

      if (seen) {
        toast.show(
          `Printerga yuborilmadi: ${(error as Error).message}. Brauzer orqali chop etiladi.`,
          'error',
        )
      }

      return false
    }
  }

  async function printReceipt(sale: Sale): Promise<boolean> {
    const auth = useAuthStore()
    const payload = agentApi.receiptPayload(sale, auth.shop?.shop_name ?? '')

    return trySend(() => agentApi.sendReceipt(payload), `${sale.number} — printerga yuborildi`)
  }

  async function printLabels(items: LabelItem[]): Promise<boolean> {
    const auth = useAuthStore()
    const job = agentApi.labelJob(items, auth.shop)

    if (job.labels.length === 0) return false

    const count = job.labels.reduce((sum, label) => sum + label.quantity, 0)

    return trySend(() => agentApi.sendLabels(job), `${count} ta yorliq printerga yuborildi`)
  }

  return { health, checked, available, version, printers, probe, printReceipt, printLabels }
})
