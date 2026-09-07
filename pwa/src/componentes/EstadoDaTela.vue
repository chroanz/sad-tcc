<script setup lang="ts">
/**
 * Componente único para os três estados que toda tela que carrega dados precisa
 * cobrir: carregando, erro e vazio. Centralizar aqui evita que uma tela nova
 * esqueça algum deles e mostre tela branca.
 */
defineProps<{
  carregando?: boolean
  erro?: string | null
  vazio?: boolean
  mensagemCarregando?: string
  mensagemVazio?: string
}>()

defineEmits<{ (evento: 'tentarNovamente'): void }>()
</script>

<template>
  <p v-if="carregando" class="cartao estado" role="status" aria-live="polite">
    <span class="girando" aria-hidden="true"></span>
    {{ mensagemCarregando ?? 'Carregando…' }}
  </p>

  <div v-else-if="erro" class="aviso erro" role="alert">
    <p>{{ erro }}</p>
    <button type="button" class="secundario" @click="$emit('tentarNovamente')">
      Tentar novamente
    </button>
  </div>

  <div v-else-if="vazio" class="cartao estado vazio">
    <p>{{ mensagemVazio ?? 'Nada por aqui ainda.' }}</p>
    <slot name="acao" />
  </div>

  <slot v-else />
</template>

<style scoped>
.estado {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: var(--cor-texto-suave);
}

.vazio {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
}

.girando {
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--cor-borda);
  border-top-color: var(--cor-primaria);
  border-radius: 50%;
  animation: girar 0.8s linear infinite;
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .girando {
    animation: none;
  }
}
</style>
