<script setup lang="ts">
/**
 * Componente único para os três estados que toda tela que carrega dados precisa
 * cobrir: carregando, erro e vazio. Centralizar aqui evita que uma tela nova
 * esqueça algum deles e mostre tela branca.
 */
withDefaults(
  defineProps<{
    carregando?: boolean
    erro?: string | null
    vazio?: boolean
    mensagemCarregando?: string
    mensagemVazio?: string
    /** Quantos esqueletos desenhar enquanto os dados não chegam. */
    esqueletos?: number
  }>(),
  { esqueletos: 3 }
)

defineEmits<{ (evento: 'tentarNovamente'): void }>()
</script>

<template>
  <!--
    Esqueleto no lugar de girador: a tela já nasce com a forma do conteúdo que vem, então
    nada salta de lugar quando ele chega.
  -->
  <div v-if="carregando" role="status" aria-live="polite">
    <span class="oculto-visual">{{ mensagemCarregando ?? 'Carregando…' }}</span>
    <div v-for="indice in esqueletos" :key="indice" class="cartao" aria-hidden="true">
      <div class="esqueleto esqueleto--titulo"></div>
      <div class="esqueleto esqueleto--linha"></div>
      <div class="esqueleto esqueleto--linha esqueleto--curta"></div>
    </div>
  </div>

  <div v-else-if="erro" class="cartao" role="alert">
    <p class="aviso aviso--erro">{{ erro }}</p>
    <button
      type="button"
      class="botao botao--secundario botao--pequeno"
      @click="$emit('tentarNovamente')"
    >
      Tentar novamente
    </button>
  </div>

  <div v-else-if="vazio" class="cartao vazio">
    <span class="vazio__sinal" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M6 6h13l-1.4 8H7.2L6 6z" />
        <path d="M6 6L5.2 3H3" />
        <circle cx="9" cy="19" r="1.4" />
        <circle cx="17" cy="19" r="1.4" />
      </svg>
    </span>
    <p>{{ mensagemVazio ?? 'Nada por aqui ainda.' }}</p>
    <slot name="acao" />
  </div>

  <slot v-else />
</template>

<style scoped>
.vazio {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--esp-3);
  padding: var(--esp-8) var(--esp-4);
  color: var(--cor-texto-suave);
}

.vazio p {
  margin: 0;
  max-width: 34ch;
  font-size: var(--fonte-pequena);
}

.vazio__sinal {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--cor-marca-tenue);
  color: var(--cor-marca-forte);
}

.vazio__sinal svg {
  width: 28px;
  height: 28px;
}
</style>
