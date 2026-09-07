<script setup lang="ts">
import type { PerfilConveniencia } from '@/api/tipos'

/**
 * O usuário não sabe o que é peso multiobjetivo, então cada perfil se apresenta pelo
 * efeito prático que produz na compra, não pelo parâmetro que altera no modelo.
 */
interface OpcaoDePerfil {
  valor: PerfilConveniencia
  titulo: string
  explicacao: string
}

const opcoes: OpcaoDePerfil[] = [
  {
    valor: 'economico',
    titulo: 'Econômico',
    explicacao: 'Menor preço possível, mesmo que precise visitar mais mercados.'
  },
  {
    valor: 'equilibrado',
    titulo: 'Equilibrado',
    explicacao: 'Pondera o quanto se economiza contra o quanto se anda.'
  },
  {
    valor: 'conveniente',
    titulo: 'Conveniente',
    explicacao: 'Concentra a compra em poucos mercados, mesmo pagando um pouco mais.'
  }
]

const perfil = defineModel<PerfilConveniencia>({ required: true })
</script>

<template>
  <fieldset class="seletor">
    <legend>Como você quer comprar?</legend>

    <label v-for="opcao in opcoes" :key="opcao.valor" class="opcao">
      <input v-model="perfil" type="radio" :value="opcao.valor" name="perfil" />
      <span class="texto">
        <strong>{{ opcao.titulo }}</strong>
        <span class="suave">{{ opcao.explicacao }}</span>
      </span>
    </label>
  </fieldset>
</template>

<style scoped>
.seletor {
  border: none;
  padding: 0;
  margin: 0 0 1rem;
}

legend {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--cor-texto-suave);
  padding: 0;
  margin-bottom: 0.4rem;
}

.opcao {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  min-height: var(--alvo-toque);
  padding: 0.6rem;
  margin-bottom: 0.4rem;
  background: var(--cor-superficie);
  border: 1px solid var(--cor-borda);
  border-radius: var(--raio);
  cursor: pointer;
}

.opcao:has(input:checked) {
  border-color: var(--cor-primaria);
  box-shadow: 0 0 0 1px var(--cor-primaria);
}

.opcao input {
  width: auto;
  min-height: auto;
  margin-top: 0.25rem;
  accent-color: var(--cor-primaria);
}

.texto {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
</style>
