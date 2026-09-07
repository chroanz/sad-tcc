<script setup lang="ts">
import { computed } from 'vue'
import { PERFIS, type ResultadosPorPerfil } from '@/stores/recomendacao'
import { TOLERANCIA_KM, compararPerfis } from '@/utilitarios/comparacao'
import { formatarDistancia, formatarReais } from '@/utilitarios/formato'
import type { PerfilConveniencia, Recomendacao } from '@/api/tipos'

/**
 * Escolher o perfil e ver a consequência da escolha são a mesma decisão, então são o mesmo
 * controle: cada opção carrega o que aquele perfil custa e o quanto obriga a andar. Sem
 * isso o usuário precisaria gerar um perfil, memorizar os números, gerar outro e comparar
 * de cabeça — justamente o trade-off que o sistema existe para tornar visível.
 */
const props = defineProps<{ resultados?: ResultadosPorPerfil | null }>()

const perfil = defineModel<PerfilConveniencia>({ required: true })

const TEXTOS: Record<PerfilConveniencia, { titulo: string; explicacao: string }> = {
  economico: {
    titulo: 'Econômico',
    explicacao: 'Menor preço possível, mesmo visitando mais mercados.'
  },
  equilibrado: {
    titulo: 'Equilibrado',
    explicacao: 'Pondera o quanto se economiza contra o quanto se anda.'
  },
  conveniente: {
    titulo: 'Conveniente',
    explicacao: 'Concentra a compra em poucos mercados, pagando um pouco mais.'
  }
}

interface OpcaoDePerfil {
  valor: PerfilConveniencia
  titulo: string
  explicacao: string
  resultado: Recomendacao | null
  selos: string[]
  comparativo: string | null
}

const disponiveis = computed<Recomendacao[]>(() =>
  PERFIS.map((valor) => props.resultados?.[valor] ?? null).filter(
    (item): item is Recomendacao => item !== null
  )
)

const menorPreco = computed<number | null>(() =>
  disponiveis.value.length === 0
    ? null
    : Math.min(...disponiveis.value.map((item) => item.custo_itens_centavos))
)

const menorPercurso = computed<number | null>(() =>
  disponiveis.value.length === 0
    ? null
    : Math.min(...disponiveis.value.map((item) => item.distancia_total_km))
)

const selecionado = computed<Recomendacao | null>(
  () => props.resultados?.[perfil.value] ?? null
)

function compararComSelecionado(candidato: Recomendacao): string | null {
  const referencia = selecionado.value
  if (referencia === null || referencia.id === candidato.id) return null
  return compararPerfis(referencia, candidato).resumo
}

function selosDe(resultado: Recomendacao): string[] {
  const selos: string[] = []
  if (resultado.custo_itens_centavos === menorPreco.value) selos.push('Mais barato')
  if (
    menorPercurso.value !== null &&
    Math.abs(resultado.distancia_total_km - menorPercurso.value) < TOLERANCIA_KM
  ) {
    selos.push('Menos percurso')
  }
  return selos
}

const opcoes = computed<OpcaoDePerfil[]>(() =>
  PERFIS.map((valor) => {
    const resultado = props.resultados?.[valor] ?? null
    return {
      valor,
      titulo: TEXTOS[valor].titulo,
      explicacao: TEXTOS[valor].explicacao,
      resultado,
      selos: resultado ? selosDe(resultado) : [],
      comparativo: resultado ? compararComSelecionado(resultado) : null
    }
  })
)
</script>

<template>
  <fieldset class="seletor">
    <legend>Como você quer comprar?</legend>

    <div class="opcoes">
      <label v-for="opcao in opcoes" :key="opcao.valor" class="opcao">
        <input v-model="perfil" type="radio" :value="opcao.valor" name="perfil" />

        <span class="conteudo-opcao">
          <span class="topo">
            <strong>{{ opcao.titulo }}</strong>
            <span v-for="selo in opcao.selos" :key="selo" class="selo selo--destaque">
              {{ selo }}
            </span>
          </span>

          <span v-if="opcao.resultado" class="numeros">
            <span class="valor preco">
              {{ formatarReais(opcao.resultado.custo_itens_centavos) }}
            </span>
            <span class="mini">
              {{ opcao.resultado.quantidade_mercados_visitados }} mercado(s) ·
              {{ formatarDistancia(opcao.resultado.distancia_total_km) }}
            </span>
          </span>

          <span class="mini">{{ opcao.explicacao }}</span>

          <span v-if="opcao.comparativo" class="comparativo">{{ opcao.comparativo }}</span>
        </span>
      </label>
    </div>
  </fieldset>
</template>

<style scoped>
.seletor {
  border: none;
  padding: 0;
  margin: 0;
}

legend {
  padding: 0;
  margin-bottom: var(--esp-2);
  font-size: var(--fonte-pequena);
  font-weight: var(--peso-medio);
  color: var(--cor-texto-suave);
}

.opcoes {
  display: grid;
  gap: var(--esp-2);
}

.opcao {
  display: flex;
  align-items: flex-start;
  gap: var(--esp-3);
  min-height: var(--alvo-confortavel);
  padding: var(--esp-3);
  background: var(--cor-superficie);
  border: 1px solid var(--cor-borda-forte);
  border-radius: var(--raio);
  cursor: pointer;
  transition: border-color var(--transicao), background var(--transicao);
}

.opcao:has(input:checked) {
  border-color: var(--cor-marca);
  background: var(--cor-marca-tenue);
  box-shadow: 0 0 0 1px var(--cor-marca);
}

.opcao input {
  width: auto;
  min-height: auto;
  margin-top: var(--esp-1);
  accent-color: var(--cor-marca);
}

.conteudo-opcao {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.topo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--esp-2);
}

.numeros {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--esp-2);
  margin: var(--esp-1) 0;
}

.preco {
  font-size: var(--fonte-grande);
  letter-spacing: -0.02em;
}

.comparativo {
  margin-top: var(--esp-1);
  font-size: var(--fonte-mini);
  color: var(--cor-texto-suave);
  font-style: italic;
}

@media (min-width: 720px) {
  .opcoes {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
