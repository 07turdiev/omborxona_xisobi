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

  /** Agent bormi — 300 ms kutadi, keyin yo'q deb hisoblaydi. */
  async function probe(): Promise<boolean> {
    health.value = await agentApi.health()
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
    // Agent brauzerdan keyin ko'tarilgan bo'lishi mumkin: kompyuter
    // yoqilganda brauzer avval ochiladi, printer esa sug'urilib-ulanadi.
    // Shuning uchun «yo'q» degan javob oxirgi so'z emas — har chop
    // etishdan oldin bir marta qayta so'raymiz. Usiz kun boshida bitta
    // muvaffaqiyatsiz tekshiruv butun kunni brauzer oynasiga bog'lardi.
    if (!available.value && !(await probe())) return false

    const toast = useToastStore()

    try {
      await send()
      toast.show(done)

      return true
    } catch (error) {
      toast.show(
        `Printerga yuborilmadi: ${(error as Error).message}. Brauzer orqali chop etiladi.`,
        'error',
      )

      // Sabab Sozlamalarda ko'rinsin (agent oxirgi xatoni eslab qoladi)
      void probe()

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
