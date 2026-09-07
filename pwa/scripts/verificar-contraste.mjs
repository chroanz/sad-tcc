/**
 * Portão de acessibilidade do sistema visual.
 *
 * Lê os tokens direto de `src/estilos/base.css` — em vez de repetir as cores aqui — e
 * confere cada par que a interface realmente usa contra os mínimos da WCAG 2.1:
 * 4,5:1 para texto (1.4.3) e 3:1 para o limite de um controle (1.4.11).
 *
 * Uso: npm run verificar-contraste
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..')
const CAMINHO_CSS = join(RAIZ, 'src', 'estilos', 'base.css')

const MINIMO_TEXTO = 4.5
const MINIMO_COMPONENTE = 3

/* ---------- Leitura dos tokens ---------- */

/** Separa o corpo do bloco de modo escuro do resto da folha, contando chaves. */
function separarPorModo(css) {
  const marcador = '@media (prefers-color-scheme: dark)'
  const inicio = css.indexOf(marcador)
  if (inicio === -1) return { claro: css, escuro: '' }

  const abertura = css.indexOf('{', inicio)
  let profundidade = 0
  let fim = abertura

  for (let i = abertura; i < css.length; i += 1) {
    if (css[i] === '{') profundidade += 1
    if (css[i] === '}') {
      profundidade -= 1
      if (profundidade === 0) {
        fim = i
        break
      }
    }
  }

  return {
    claro: css.slice(0, inicio) + css.slice(fim + 1),
    escuro: css.slice(abertura, fim)
  }
}

function extrairTokens(trecho) {
  const tokens = new Map()
  const padrao = /(--[a-z0-9-]+)\s*:\s*([^;]+);/gi
  let achado = padrao.exec(trecho)
  while (achado !== null) {
    tokens.set(achado[1], achado[2].trim())
    achado = padrao.exec(trecho)
  }
  return tokens
}

/** Resolve `var(--x)` em cadeia; o modo escuro herda o que não redefiniu. */
function resolver(nome, tokensDoModo, tokensClaro, visitados = new Set()) {
  if (visitados.has(nome)) throw new Error(`Referência circular em ${nome}`)
  visitados.add(nome)

  const bruto = tokensDoModo.get(nome) ?? tokensClaro.get(nome)
  if (bruto === undefined) throw new Error(`Token não encontrado: ${nome}`)

  const referencia = bruto.match(/^var\((--[a-z0-9-]+)\)$/i)
  if (referencia === null) return bruto
  return resolver(referencia[1], tokensDoModo, tokensClaro, visitados)
}

/* ---------- Contraste WCAG ---------- */

function canalLinear(valor) {
  const v = valor / 255
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
}

function luminancia(hex) {
  const limpo = hex.replace('#', '')
  const completo =
    limpo.length === 3
      ? limpo
          .split('')
          .map((c) => c + c)
          .join('')
      : limpo
  const numero = Number.parseInt(completo, 16)
  return (
    0.2126 * canalLinear((numero >> 16) & 255) +
    0.7152 * canalLinear((numero >> 8) & 255) +
    0.0722 * canalLinear(numero & 255)
  )
}

function contraste(frente, fundo) {
  const a = luminancia(frente)
  const b = luminancia(fundo)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

/* ---------- Pares verificados ---------- */

const PARES = [
  ['texto sobre superfície', '--cor-texto', '--cor-superficie', MINIMO_TEXTO],
  ['texto suave sobre superfície', '--cor-texto-suave', '--cor-superficie', MINIMO_TEXTO],
  [
    'texto suave sobre superfície alternativa',
    '--cor-texto-suave',
    '--cor-superficie-alt',
    MINIMO_TEXTO
  ],
  ['rótulo do botão primário', '--cor-texto-inverso', '--cor-marca', MINIMO_TEXTO],
  ['link e marca forte sobre superfície', '--cor-marca-forte', '--cor-superficie', MINIMO_TEXTO],
  ['selo de marca', '--cor-marca-forte', '--cor-marca-tenue', MINIMO_TEXTO],
  ['selo de destaque', '--cor-destaque-texto', '--cor-destaque-tenue', MINIMO_TEXTO],
  ['aviso de erro', '--cor-erro-texto', '--cor-erro-tenue', MINIMO_TEXTO],
  ['ação destrutiva sobre superfície', '--cor-erro-texto', '--cor-superficie', MINIMO_TEXTO],
  ['contorno de campo e chip', '--cor-borda-forte', '--cor-superficie', MINIMO_COMPONENTE],
  ['anel de foco sobre superfície', '--cor-foco', '--cor-superficie', MINIMO_COMPONENTE]
]

/* ---------- Execução ---------- */

const css = readFileSync(CAMINHO_CSS, 'utf8')
const { claro, escuro } = separarPorModo(css)
const tokensClaro = extrairTokens(claro)
const tokensEscuro = extrairTokens(escuro)

let reprovados = 0

for (const [modo, tokens] of [
  ['claro', tokensClaro],
  ['escuro', tokensEscuro]
]) {
  console.log(`\nModo ${modo}`)
  for (const [rotulo, frente, fundo, minimo] of PARES) {
    const corFrente = resolver(frente, tokens, tokensClaro)
    const corFundo = resolver(fundo, tokens, tokensClaro)
    const razao = contraste(corFrente, corFundo)
    const passou = razao >= minimo
    if (!passou) reprovados += 1
    console.log(
      `  ${passou ? 'OK   ' : 'FALHA'} ${razao.toFixed(2).padStart(5)}:1  ` +
        `(mín. ${minimo})  ${rotulo}  ${corFrente} sobre ${corFundo}`
    )
  }
}

const total = PARES.length * 2
console.log(`\n${total} pares verificados, ${reprovados} reprovado(s).`)
process.exit(reprovados === 0 ? 0 : 1)
