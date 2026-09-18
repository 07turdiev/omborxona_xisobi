/**
 * Mahsulot sahifasidagi tanlov mantiqi: rang → galereya, rang → o'lcham
 * qoldig'i, rang + o'lcham → variant (shtrix-kod).
 *
 * Sof funksiyalar — komponentdan ajratilgan, shuning uchun alohida
 * sinaladi (`catalog.spec.ts`).
 */

import type { CatalogProduct, CatalogVariant, ImageGroup, ProductImage } from '@/types'

export interface SizeOption {
  id: number
  name: string
  /** Tanlangan rangdagi qoldiq; rang tanlanmagan bo'lsa — hamma ranglar */
  quantity: number
}

function sum(variants: CatalogVariant[]): number {
  return variants.reduce((total, variant) => total + variant.stock_quantity, 0)
}

/** Rangning hamma o'lchamlardagi qoldig'i. */
export function colorStock(product: CatalogProduct, colorId: number): number {
  return sum(product.variants.filter((variant) => variant.color === colorId))
}

/**
 * O'lcham tugmalari: mahsulotning **hamma** o'lchamlari, qoldig'i
 * tanlangan rang bo'yicha. Qoldig'i nol o'lcham ham ro'yxatda qoladi —
 * u faqat o'chirilgan ko'rinishda chiqadi.
 */
export function sizeOptions(product: CatalogProduct, colorId: number | null): SizeOption[] {
  return product.sizes.map((size) => ({
    id: size.id,
    name: size.name,
    quantity: sum(
      product.variants.filter(
        (variant) => variant.size === size.id && (colorId === null || variant.color === colorId),
      ),
    ),
  }))
}

/**
 * Galereyadagi rasmlar: tanlangan rangniki, keyin umumiylari.
 *
 * Rangning o'z rasmi ham, umumiy rasm ham bo'lmasa — hamma rasmlar
 * ko'rsatiladi: bo'sh galereyadan boshqa rangdagi surat yaxshiroq.
 */
export function galleryImages(groups: ImageGroup[], colorId: number | null): ProductImage[] {
  const all = groups.flatMap((group) => group.images)

  if (colorId === null) {
    // Asosiy rasm birinchi turadi
    return [...all].sort((a, b) => Number(b.is_primary) - Number(a.is_primary))
  }

  const own = groups.find((group) => group.color === colorId)?.images ?? []
  const general = groups.find((group) => group.color === null)?.images ?? []
  const images = [...own, ...general]

  return images.length ? images : all
}

/**
 * Sahifa ochilganda qaysi rang tanlanadi: asosiy rasmning rangi, u
 * bo'lmasa qoldig'i bor birinchi rang, u ham bo'lmasa birinchisi.
 */
export function initialColor(product: CatalogProduct): number | null {
  if (!product.colors.length) return null

  const primary = product.image_groups
    .flatMap((group) => group.images)
    .find((image) => image.is_primary)

  if (primary?.color != null && product.colors.some((color) => color.id === primary.color)) {
    return primary.color
  }

  const withStock = product.colors.find((color) => colorStock(product, color.id) > 0)

  return (withStock ?? product.colors[0]!).id
}

/**
 * Tanlangan o'lcham va rangga mos variant. Tanlov to'liq bo'lmasa —
 * `null`: bitta shtrix-kodni aniq aytib bo'lmaydi.
 */
export function findVariant(
  product: CatalogProduct,
  sizeId: number | null,
  colorId: number | null,
): CatalogVariant | null {
  const needsSize = product.sizes.length > 0
  const needsColor = product.colors.length > 0

  if ((needsSize && sizeId === null) || (needsColor && colorId === null)) return null

  return (
    product.variants.find(
      (variant) =>
        (!needsSize || variant.size === sizeId) && (!needsColor || variant.color === colorId),
    ) ?? null
  )
}
