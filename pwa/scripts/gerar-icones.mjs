// Gera os icones PNG do PWA (192 e 512) sem depender de biblioteca externa.
// Executar com: npm run gerar-icones
import { deflateSync } from 'node:zlib'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..')
const DESTINO = join(RAIZ, 'public')

const VERDE = [31, 122, 77]
const BRANCO = [255, 255, 255]

function tabelaCrc() {
  const tabela = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    tabela[n] = c >>> 0
  }
  return tabela
}
const CRC = tabelaCrc()

function crc32(buffer) {
  let c = 0xffffffff
  for (const byte of buffer) c = CRC[(c ^ byte) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}

function pedaco(tipo, dados) {
  const tamanho = Buffer.alloc(4)
  tamanho.writeUInt32BE(dados.length, 0)
  const corpo = Buffer.concat([Buffer.from(tipo, 'ascii'), dados])
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(corpo), 0)
  return Buffer.concat([tamanho, corpo, crc])
}

function codificarPng(largura, altura, pixels) {
  const assinatura = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(largura, 0)
  ihdr.writeUInt32BE(altura, 4)
  ihdr[8] = 8 // profundidade de bits
  ihdr[9] = 6 // RGBA
  const bruto = Buffer.alloc(altura * (1 + largura * 4))
  for (let y = 0; y < altura; y++) {
    const inicio = y * (1 + largura * 4)
    bruto[inicio] = 0 // filtro "none"
    pixels.copy(bruto, inicio + 1, y * largura * 4, (y + 1) * largura * 4)
  }
  return Buffer.concat([
    assinatura,
    pedaco('IHDR', ihdr),
    pedaco('IDAT', deflateSync(bruto, { level: 9 })),
    pedaco('IEND', Buffer.alloc(0))
  ])
}

function dentroDoRetanguloArredondado(x, y, x0, y0, x1, y1, raio) {
  if (x < x0 || x > x1 || y < y0 || y > y1) return false
  const cx = Math.min(Math.max(x, x0 + raio), x1 - raio)
  const cy = Math.min(Math.max(y, y0 + raio), y1 - raio)
  return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2
}

function desenhar(tamanho) {
  const pixels = Buffer.alloc(tamanho * tamanho * 4)
  const u = (v) => v * tamanho
  for (let y = 0; y < tamanho; y++) {
    for (let x = 0; x < tamanho; x++) {
      const i = (y * tamanho + x) * 4
      const px = x + 0.5
      const py = y + 0.5
      const noFundo = dentroDoRetanguloArredondado(px, py, 0, 0, tamanho, tamanho, u(0.22))
      if (!noFundo) continue

      let cor = VERDE
      const corpoSacola = dentroDoRetanguloArredondado(
        px,
        py,
        u(0.24),
        u(0.4),
        u(0.76),
        u(0.82),
        u(0.07)
      )
      const dx = px - u(0.5)
      const dy = py - u(0.42)
      const distancia = Math.sqrt(dx * dx + dy * dy)
      const alca = dy <= 0 && distancia <= u(0.19) && distancia >= u(0.13)
      if (corpoSacola || alca) cor = BRANCO

      // Duas faixas verdes na sacola sugerindo itens da lista.
      if (corpoSacola) {
        const faixa1 = py > u(0.53) && py < u(0.575) && px > u(0.33) && px < u(0.67)
        const faixa2 = py > u(0.63) && py < u(0.675) && px > u(0.33) && px < u(0.6)
        if (faixa1 || faixa2) cor = VERDE
      }

      pixels[i] = cor[0]
      pixels[i + 1] = cor[1]
      pixels[i + 2] = cor[2]
      pixels[i + 3] = 255
    }
  }
  return codificarPng(tamanho, tamanho, pixels)
}

mkdirSync(DESTINO, { recursive: true })
for (const tamanho of [192, 512]) {
  const arquivo = join(DESTINO, `icone-${tamanho}.png`)
  writeFileSync(arquivo, desenhar(tamanho))
  console.log(`gerado: ${arquivo}`)
}
