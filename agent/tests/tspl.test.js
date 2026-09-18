import assert from 'node:assert/strict'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'node:test'

import { buildLabels, DOTS_PER_MM } from '../src/tspl.js'

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
    assert.match(text(), /BARCODE 20,\d+,"EAN13",90,1,0,2,2,"2000000000015"/)
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
    assert.match(risky, /TEXT 12,30,"2",0,1,1,"Koylaktest"/)
  })

  it('shtrix-kod yorliq ichida qoladi', () => {
    const height = 30 * DOTS_PER_MM
    const [, y] = /BARCODE 20,(\d+),/.exec(text())

    assert.ok(Number(y) > 0)
    assert.ok(Number(y) + 90 <= height, 'kod yorliqdan chiqib ketgan')
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
    assert.match(commands, /BARCODE 20,110,"EAN13",90,1,0,2,2,"2000000000015"/)
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
