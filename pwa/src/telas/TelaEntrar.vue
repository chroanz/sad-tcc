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
    <h1>Compra Certa</h1>
    <p class="suave">
      Monte sua lista e descubra em quais supermercados de Juazeiro do Norte comprar cada
      item, equilibrando preço e deslocamento.
    </p>

    <form class="cartao" novalidate @submit.prevent="enviar">
      <h2>{{ titulo }}</h2>

      <p v-if="sessao.erro" class="aviso erro" role="alert">{{ sessao.erro }}</p>

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
        <small v-if="modoCadastro" class="suave">Mínimo de 8 caracteres.</small>
      </label>

      <button type="submit" class="largura-total" :disabled="sessao.carregando">
        {{ sessao.carregando ? 'Enviando…' : titulo }}
      </button>

      <button type="button" class="discreto largura-total" @click="alternarModo">
        {{ modoCadastro ? 'Já tenho conta' : 'Criar uma conta' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.abertura {
  max-width: 420px;
  margin: 1rem auto;
}
</style>
