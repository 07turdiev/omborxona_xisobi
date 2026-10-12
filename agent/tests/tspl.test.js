import assert from 'node:assert/strict'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'node:test'

import { buildLabels, buildShelfLabels, DOTS_PER_MM } from '../src/tspl.js'

const HERE = dirname(fileURLToPath(import.meta.url))
const FIXTURE = join(HERE, 'fixtures', 'label.hex')

const JOB = {
  widthMm: 40,
  heightMm: 30,
  gapMm: 2,
  labels: [
    {
      shopName: 'Madlen sen',
      name: 'Yozgi koʻylak',
      variant: 'M / Oq',
      price: '250 000 so‘m',
      barcode: '2000000000015',
      quantity: 3,
    },
  ],
}

const text = () => buildLabels(JOB).toString('latin1')

describe('buildLabels — tuzilishi', () => {
  it('o‘lcham va oraliq bir marta beriladi', () => {
    const commands = text()

    assert.match(commands, /^SIZE 40 mm,30 mm\r\n/)
    assert.match(commands, /GAP 2 mm,0 mm/)
    assert.equal(commands.match(/SIZE /g).length, 1)
    assert.equal(commands.match(/GAP /g).length, 1)
  })

  it('zichlik va tezlik sozlanadi', () => {
    const commands = buildLabels(JOB, { density: 12, speed: 2 }).toString('latin1')

    assert.match(commands, /DENSITY 12/)
    assert.match(commands, /SPEED 2/)
  })

  it('EAN-13 ni printerning o‘zi chizadi', () => {
    assert.match(text(), /BARCODE 65,\d+,"EAN13",90,1,0,2,2,"2000000000015"/)
  })

  it('nusxalar soni PRINT buyrug‘ida beriladi', () => {
    assert.match(text(), /PRINT 3,1/)
  })

  it('yorliqlar orasida FORMFEED yo‘q — bo‘sh yorliq chiqmaydi', () => {
    const many = buildLabels({
      ...JOB,
      labels: [JOB.labels[0], { ...JOB.labels[0], barcode: '2000000000022', quantity: 1 }],
    }).toString('latin1')

    assert.equal(many.includes('FORMFEED'), false)
    assert.equal(many.match(/CLS/g).length, 2)
    assert.equal(many.match(/PRINT /g).length, 2)
  })

  it("o'zbekcha belgilar oddiy apostrofga aylanadi", () => {
    const commands = text()

    assert.ok(commands.includes("Yozgi ko'ylak"))
    assert.equal(commands.includes('ʻ'), false)
  })

  it('qo‘shtirnoq buyruqni buzmaydi', () => {
    const risky = buildLabels({
      ...JOB,
      labels: [{ ...JOB.labels[0], name: 'Ko"ylak\\test' }],
    }).toString('latin1')

    assert.equal(risky.includes('"Ko"ylak'), false)
    assert.match(risky, /TEXT \d+,30,"2",0,1,1,"Koylaktest"/)
  })

  it('shtrix-kod yorliq ichida qoladi', () => {
    const height = 30 * DOTS_PER_MM
    const [, y] = /BARCODE \d+,(\d+),/.exec(text())

    assert.ok(Number(y) > 0)
    assert.ok(Number(y) + 90 <= height, 'kod yorliqdan chiqib ketgan')
  })

  it('mazmun yorliq o‘rtasida turadi', () => {
    // Qurilmada tekshirilgan: markazlashtirilmasa chizma chapga
    // surilib qoladi va o'ngda ~14 mm bo'sh joy qoladi
    const width = 40 * DOTS_PER_MM
    const commands = text()

    // EAN-13 doim 95 modul: (320 - 95*2) / 2 = 65
    assert.match(commands, /BARCODE 65,/)

    for (const [, x, font, value] of commands.matchAll(/TEXT (\d+),\d+,"(\d)",0,1,1,"([^"]*)"/g)) {
      const fontWidth = { 1: 8, 2: 12, 3: 16 }[font]

      const left = Number(x)
      const right = width - (left + value.length * fontWidth)

      // Yaxlitlash tufayli bir nuqta farq bo'lishi mumkin
      assert.ok(
        Math.abs(left - right) <= 1,
        `"${value}" markazda emas: chapda ${left}, o‘ngda ${right} nuqta`,
      )
    }
  })

  it('yorliq kengaysa markaz ham suriladi', () => {
    const wide = buildLabels({ ...JOB, widthMm: 60 }).toString('latin1')

    // (60*8 - 190) / 2 = 145
    assert.match(wide, /BARCODE 145,/)
  })

  it('miqdor ko‘rsatilmasa bitta yorliq', () => {
    const single = buildLabels({
      ...JOB,
      labels: [{ ...JOB.labels[0], quantity: undefined }],
    }).toString('latin1')

    assert.match(single, /PRINT 1,1/)
  })
})

describe('buildLabels — to‘liq bo‘lmagan sozlama', () => {
  /** `config.json` da faqat `transport` va `share` bo'lgan holat */
  const fromMinimalConfig = {
    density: undefined,
    speed: undefined,
    barcodeHeight: undefined,
  }

  it('standart qiymatlar saqlanadi — natija to‘liq sozlama bilan bir xil', () => {
    assert.deepEqual(buildLabels(JOB, fromMinimalConfig), buildLabels(JOB))
  })

  it('so‘rovda o‘lcham bo‘lmasa 40×30 mm olinadi', () => {
    const commands = buildLabels({ labels: JOB.labels }, fromMinimalConfig).toString('latin1')

    assert.match(commands, /SIZE 40 mm,30 mm/)
    assert.match(commands, /GAP 2 mm,0 mm/)
    assert.match(commands, /DENSITY 8/)
    assert.match(commands, /SPEED 4/)
  })

  it('shtrix-kod buyrug‘i to‘liq bo‘ladi', () => {
    const commands = buildLabels(JOB, fromMinimalConfig).toString('latin1')

    // Ilgari shunday chiqardi: BARCODE 20,NaN,"EAN13",undefined,...
    assert.match(commands, /BARCODE 65,110,"EAN13",90,1,0,2,2,"2000000000015"/)
  })

  it('buyruqlarda "undefined" yoki "NaN" bo‘lmaydi', () => {
    const commands = buildLabels(JOB, fromMinimalConfig).toString('latin1')

    assert.equal(commands.includes('undefined'), false)
    assert.equal(commands.includes('NaN'), false)
  })

  it('uzluksiz lentada oraliq 0 bo‘la oladi', () => {
    const commands = buildLabels({ ...JOB, gapMm: 0 }).toString('latin1')

    assert.match(commands, /GAP 0 mm,0 mm/)
  })
})

describe('buildShelfLabels — javon yorlig‘i', () => {
  const SHELVES = {
    widthMm: 40,
    heightMm: 30,
    gapMm: 2,
    labels: [{ cell: 'A1', quantity: 1 }],
  }

  const shelf = (labels, job = SHELVES) =>
    buildShelfLabels({ ...job, labels }).toString('latin1')

  /** `TEXT x,y,"5",0,eni,bo'yi,"A1"` dan sonlarni ajratib oladi */
  function code(commands) {
    const [, x, y, wide, tall, value] =
      /TEXT (\d+),(\d+),"5",0,(\d+),(\d+),"([^"]*)"/.exec(commands)

    return { x: +x, y: +y, wide: +wide, tall: +tall, value }
  }

  it('o‘lcham, oraliq va zichlik mahsulot yorlig‘idagidek', () => {
    const commands = buildShelfLabels(SHELVES, { density: 12, speed: 2 }).toString('latin1')

    assert.match(commands, /^SIZE 40 mm,30 mm\r\nGAP 2 mm,0 mm\r\n/)
    assert.match(commands, /DENSITY 12/)
    assert.match(commands, /SPEED 2/)
    assert.equal(commands.includes('BARCODE'), false)
  })

  it('yorliqda faqat manzil — o‘rtada, 12 mm balandlikda', () => {
    const commands = shelf(SHELVES.labels)

    // Bitta TEXT: qator nomi va boshqa yozuv yo'q
    assert.equal(commands.match(/TEXT /g).length, 1)

    // 12 mm = 96 nuqta = 48 × 2. O'rtasi: (320 - 2*32*2) / 2 = 96,
    // (240 - 96) / 2 = 72
    assert.deepEqual(code(commands), { x: 96, y: 72, wide: 2, tall: 2, value: 'A1' })
  })

  it('harf balandligini so‘rov beradi', () => {
    const big = code(shelf(SHELVES.labels, { ...SHELVES, textMm: 18 }))

    // 18 mm = 144 nuqta = 48 × 3
    assert.equal(big.tall, 3)
    assert.equal(big.wide, 3)
    // (240 - 144) / 2 = 48
    assert.equal(big.y, 48)
  })

  it('yorliqdan katta harf so‘ralsa — sig‘adiganigacha kichrayadi', () => {
    const huge = code(shelf(SHELVES.labels, { ...SHELVES, textMm: 100 }))

    // 30 mm yorliqqa hoshiya bilan 224 nuqta sig'adi: 48 × 4 = 192
    assert.equal(huge.tall, 4)
  })

  it('uch belgili manzil torayadi, lekin pasaymaydi', () => {
    const job = { ...SHELVES, textMm: 24 }
    const short = code(shelf([{ cell: 'A9' }], job))
    const long = code(shelf([{ cell: 'A10' }], job))

    assert.equal(long.tall, short.tall)
    assert.equal(long.wide, 3)
    // (320 - 3*32*3) / 2 = 16
    assert.equal(long.x, 16)
  })

  it('kichik harf kattaga aylanadi', () => {
    assert.equal(code(shelf([{ cell: 'd3' }])).value, 'D3')
  })

  it('manzil yorliqdan chiqib ketmaydi', () => {
    for (const [widthMm, heightMm] of [[40, 30], [58, 40], [30, 20], [100, 60]]) {
      const width = widthMm * DOTS_PER_MM
      const height = heightMm * DOTS_PER_MM

      for (const textMm of [6, 12, 24, 100]) {
        for (const cell of ['A1', 'Z30']) {
          const { x, y, wide, tall } = code(shelf([{ cell }], { widthMm, heightMm, textMm }))
          const where = `${cell}, ${textMm} mm, ${widthMm}×${heightMm}`

          assert.ok(tall >= 1 && tall <= 10 && wide >= 1 && wide <= 10, where)
          assert.ok(x + cell.length * 32 * wide <= width, `${where}: eniga sig‘madi`)
          assert.ok(y + 48 * tall <= height, `${where}: bo‘yiga sig‘madi`)
        }
      }
    }
  })

  it('har javon — alohida yorliq, nusxasi PRINT da', () => {
    const commands = shelf([
      { cell: 'A1', quantity: 2 },
      { cell: 'A2' },
    ])

    assert.equal(commands.match(/CLS/g).length, 2)
    assert.match(commands, /PRINT 2,1\r\n[\s\S]*PRINT 1,1/)
    assert.equal(commands.includes('FORMFEED'), false)
  })

  it('buyruqlarda "undefined" yoki "NaN" bo‘lmaydi', () => {
    const commands = buildShelfLabels(
      { labels: [{ cell: 'A1' }], textMm: 'katta' },
      { density: undefined, speed: undefined },
    ).toString('latin1')

    assert.match(commands, /SIZE 40 mm,30 mm/)
    // Noto'g'ri o'lchamda standart 12 mm olinadi
    assert.match(commands, /"5",0,2,2,"A1"/)
    assert.equal(commands.includes('undefined'), false)
    assert.equal(commands.includes('NaN'), false)
  })
})

describe('buildLabels — o‘zgarmaganligi (golden fixture)', () => {
  it('baytlar saqlangan namunaga aynan teng', () => {
    const current = buildLabels(JOB).toString('hex')

    if (!existsSync(FIXTURE)) {
      writeFileSync(FIXTURE, current)
      assert.fail('fixture yaratildi — testni qayta ishga tushiring')
    }

    assert.equal(current, readFileSync(FIXTURE, 'utf8').trim())
  })
})
