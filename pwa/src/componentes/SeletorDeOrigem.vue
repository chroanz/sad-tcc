<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useCatalogoStore } from '@/stores/catalogo'
import { RAIOS_KM, useOrigemStore } from '@/stores/origem'
import { distanciaKm } from '@/utilitarios/localizacao'
import type { Mercado } from '@/api/tipos'

/**
 * Ponto de partida e alcance da busca.
 *
 * O pedido de localização nunca acontece na montagem: a permissão negada é definitiva, e
 * gastar o aviso do navegador antes de o usuário entender para que serve mata o recurso
 * para sempre naquele aparelho. Por isso a explicação vem primeiro e a chamada só parte de
 * um toque.
 */
const emit = defineEmits<{ (evento: 'alterada'): void }>()

const origem = useOrigemStore()
const catalogo = useCatalogoStore()

const escolhendoReferencia = ref(false)

onMounted(() => {
  void catalogo.carregarMercados()
})

const temOrigemReal = computed<boolean>(() => origem.coordenadaParaEnvio !== undefined)

/**
 * Quantos mercados caem no raio. Antecipar isso evita o pior caminho: montar a lista,
 * gerar, e só então descobrir que o recorte deixou itens sem oferta.
 */
const mercadosNoRaio = computed<number | null>(() => {
  const ponto = origem.coordenadaParaEnvio
  if (ponto === undefined || origem.raioKm === null) return null
  return catalogo.mercados.filter(
    (mercado) =>
      distanciaKm(ponto, { latitude: mercado.latitude, longitude: mercado.longitude }) <=
      (origem.raioKm as number)
  ).length
})

async function pedirLocalizacao(): Promise<void> {
  if (await origem.usarDispositivo()) {
    escolhendoReferencia.value = false
    emit('alterada')
  } else {
    escolhendoReferencia.value = true
  }
}

function escolherReferencia(mercado: Mercado): void {
  origem.usarReferencia(mercado)
  escolhendoReferencia.value = false
  emit('alterada')
}

function voltarAoPadrao(): void {
  origem.usarPadrao()
  escolhendoReferencia.value = false
  emit('alterada')
}

function trocarRaio(km: number | null): void {
  origem.definirRaio(km)
  emit('alterada')
}

function rotuloDoRaio(km: number | null): string {
  return km === null ? 'Toda a cidade' : `${km} km`
}
</script>

<template>
  <section class="origem">
    <div class="linha-entre">
      <span class="crescer">
        <span class="rotulo">Você sai de</span>
        <strong class="descricao">{{ origem.descricao }}</strong>
      </span>
      <span v-if="temOrigemReal" class="selo selo--marca">exata</span>
      <span v-else class="selo">aproximada</span>
    </div>

    <!-- A explicação precede o pedido; o aviso do navegador só aparece após o toque. -->
    <p v-if="!temOrigemReal" class="mini explicacao">
      Usar sua localização deixa a distância e a ordem do roteiro corretas. Sem ela, o
      cálculo parte do centro de Juazeiro do Norte.
    </p>

    <p v-if="origem.erro" class="aviso aviso--atencao" role="status">{{ origem.erro }}</p>

    <div class="linha acoes">
      <button
        v-if="origem.disponivel && origem.permissao !== 'negada'"
        type="button"
        class="botao botao--secundario botao--pequeno"
        :disabled="origem.obtendo"
        @click="pedirLocalizacao"
      >
        {{ origem.obtendo ? 'Localizando…' : 'Usar minha localização' }}
      </button>

      <button
        type="button"
        class="botao botao--fantasma botao--pequeno"
        @click="escolhendoReferencia = !escolhendoReferencia"
      >
        Escolher um ponto
      </button>

      <button
        v-if="temOrigemReal"
        type="button"
        class="botao botao--fantasma botao--pequeno"
        @click="voltarAoPadrao"
      >
        Usar o centro
      </button>
    </div>

    <!--
      Alternativa para quem negou a permissão: partir de um mercado conhecido. Sem ela,
      negar seria um beco sem saída, já que a aplicação não pode perguntar de novo.
    -->
    <div v-if="escolhendoReferencia" class="referencias">
      <p class="mini">De qual mercado você sai perto?</p>
      <ul class="colecao">
        <li v-for="mercado in catalogo.mercados" :key="mercado.id">
          <button type="button" class="referencia" @click="escolherReferencia(mercado)">
            <strong>{{ mercado.nome }}</strong>
            <span class="mini">{{ mercado.endereco }}</span>
          </button>
        </li>
      </ul>
    </div>

    <div class="raio">
      <span class="rotulo">Buscar mercados até</span>
      <div class="chips">
        <button
          v-for="km in RAIOS_KM"
          :key="String(km)"
          type="button"
          class="chip"
          :class="{ 'chip--ativo': origem.raioKm === km }"
          :disabled="!temOrigemReal"
          :aria-pressed="origem.raioKm === km"
          @click="trocarRaio(km)"
        >
          {{ rotuloDoRaio(km) }}
        </button>
      </div>

      <p v-if="!temOrigemReal" class="mini">
        O raio precisa de um ponto de partida seu: medi-lo a partir do centro diria uma
        distância que não é a sua.
      </p>
      <p v-else-if="mercadosNoRaio !== null" class="mini">
        {{ mercadosNoRaio }} mercado(s) neste raio, em linha reta — o percurso de rua costuma
        ser maior.
      </p>
      <p v-else class="mini">Todos os mercados cadastrados entram no cálculo.</p>
    </div>
  </section>
</template>

<style scoped>
.origem {
  display: flex;
  flex-direction: column;
  gap: var(--esp-3);
}

.rotulo {
  display: block;
}

.descricao {
  font-size: var(--fonte-media);
  letter-spacing: -0.01em;
}

.explicacao {
  margin: 0;
}

.acoes {
  flex-wrap: wrap;
  gap: var(--esp-2);
}

.referencias {
  padding-top: var(--esp-3);
  border-top: 1px solid var(--cor-borda);
}

.referencias .mini {
  margin: 0 0 var(--esp-2);
}

.referencia {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  min-height: var(--alvo-confortavel);
  padding: var(--esp-2);
  text-align: left;
  background: none;
  border: none;
  border-bottom: 1px solid var(--cor-borda);
  border-radius: var(--raio-pequeno);
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.referencia:hover {
  background: var(--cor-superficie-alt);
}

.raio {
  padding-top: var(--esp-3);
  border-top: 1px solid var(--cor-borda);
}

.raio .chips {
  margin: var(--esp-2) 0;
}

.raio .mini {
  margin: 0;
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
