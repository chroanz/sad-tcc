<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessaoStore } from '@/stores/sessao'

const sessao = useSessaoStore()
const rota = useRoute()
const roteador = useRouter()

const modoCadastro = ref(false)
const nome = ref('')
const email = ref('')
const senha = ref('')

const titulo = computed<string>(() => (modoCadastro.value ? 'Criar conta' : 'Entrar'))

function alternarModo(): void {
  modoCadastro.value = !modoCadastro.value
  sessao.limparErro()
}

async function enviar(): Promise<void> {
  const sucesso = modoCadastro.value
    ? await sessao.cadastrar({ nome: nome.value, email: email.value, senha: senha.value })
    : await sessao.entrar({ email: email.value, senha: senha.value })

  if (sucesso) {
    const retorno = rota.query.retorno
    await roteador.push(typeof retorno === 'string' ? retorno : { name: 'listas' })
  }
}
</script>

<template>
  <section class="abertura">
    <div class="hero">
      <span class="hero__sinal" aria-hidden="true">CC</span>
      <h1>Compra Certa</h1>
      <p>
        Monte sua lista e descubra em quais supermercados de Juazeiro do Norte comprar cada
        item, equilibrando preço e deslocamento.
      </p>
    </div>

    <form class="cartao" novalidate @submit.prevent="enviar">
      <h2>{{ titulo }}</h2>

      <p v-if="sessao.erro" class="aviso aviso--erro" role="alert">{{ sessao.erro }}</p>

      <label v-if="modoCadastro" class="campo">
        <span>Nome</span>
        <input v-model="nome" type="text" autocomplete="name" required />
      </label>

      <label class="campo">
        <span>E-mail</span>
        <input v-model="email" type="email" autocomplete="email" required />
      </label>

      <label class="campo">
        <span>Senha</span>
        <input
          v-model="senha"
          type="password"
          :autocomplete="modoCadastro ? 'new-password' : 'current-password'"
          minlength="8"
          required
        />
        <small v-if="modoCadastro" class="mini">Mínimo de 8 caracteres.</small>
      </label>

      <button
        type="submit"
        class="botao botao--primario botao--bloco"
        :disabled="sessao.carregando"
      >
        {{ sessao.carregando ? 'Enviando…' : titulo }}
      </button>

      <button
        type="button"
        class="botao botao--fantasma botao--bloco alternar"
        @click="alternarModo"
      >
        {{ modoCadastro ? 'Já tenho conta' : 'Criar uma conta' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.abertura {
  max-width: 420px;
  margin: 0 auto;
  padding-top: var(--esp-6);
}

.hero {
  text-align: center;
  margin-bottom: var(--esp-6);
}

.hero__sinal {
  display: inline-grid;
  place-items: center;
  width: 60px;
  height: 60px;
  margin-bottom: var(--esp-3);
  border-radius: var(--raio-grande);
  background: var(--cor-marca);
  color: var(--cor-texto-inverso);
  font-size: var(--fonte-grande);
  font-weight: var(--peso-extra);
  letter-spacing: -0.02em;
}

.hero p {
  margin: 0;
  color: var(--cor-texto-suave);
  font-size: var(--fonte-pequena);
}

.alternar {
  margin-top: var(--esp-2);
}
</style>
