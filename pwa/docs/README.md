# PWA (`pwa/`)

Aplicativo web progressivo que o usuário usa no celular: monta a lista de compras, escolhe
o perfil e recebe o roteiro de qual mercado visitar e o que comprar em cada um.

Vue 3 (Composition API com `<script setup>`) + Vite + TypeScript + Pinia + vue-router +
`vite-plugin-pwa`. CSS próprio, sem framework de UI.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`telas-e-navegacao.md`](telas-e-navegacao.md) | cada tela, seus estados e o fluxo de navegação |
| [`estado-e-api.md`](estado-e-api.md) | stores Pinia e o cliente HTTP |
| [`pwa-e-offline.md`](pwa-e-offline.md) | manifest, service worker e o que funciona sem rede |
| [`../../docs/contrato-api-rest.md`](../../docs/contrato-api-rest.md) | o contrato com a API Go |

## Estrutura

```
pwa/
├── index.html
├── vite.config.ts              # plugin Vue + configuração do PWA
├── public/                     # ícones do manifest
├── src/
│   ├── main.ts                 # monta o app, Pinia e o roteador
│   ├── App.vue                 # casca: barra de topo e aviso de offline
│   ├── rotas/indice.ts         # rotas e guarda de autenticação
│   ├── api/                    # cliente HTTP e tipos do contrato
│   ├── stores/                 # sessao, catalogo, listas, recomendacao
│   ├── componentes/            # EstadoDaTela, SeletorDePerfil
│   ├── telas/                  # as seis telas
│   ├── utilitarios/            # formatação, armazenamento, conexão
│   └── estilos/base.css
└── docs/
```

## Como rodar

```bash
cd pwa
npm install
npm run dev          # http://localhost:5173
```

A API precisa estar de pé em `VITE_API_URL` (padrão `http://localhost:8080/api/v1`).
Sem ela, as telas carregam mas exibem mensagem de erro — nunca tela branca.

```bash
npm run build        # verifica tipos e gera dist/ com o service worker
npm run preview      # serve o build; é aqui que dá para testar a instalação e o offline
npm run verificar-tipos
```

O service worker só existe no build. Em `npm run dev` o comportamento offline não é o real.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8080/api/v1` | base da API Go |

Variáveis do Vite são lidas **no build**. Trocar o valor exige reiniciar o servidor de
desenvolvimento ou refazer o build.

## Convenções

- Componentes, funções, variáveis e arquivos em **português brasileiro**
  (`TelaResultado.vue`, `useRecomendacaoStore`, `formatarReais`).
- Campos de payload **seguem o contrato** e não são renomeados no cliente.
- Dinheiro chega em **centavos inteiros**; a divisão por 100 acontece só na apresentação,
  em `formatarReais`. Nenhum cálculo monetário é feito no frontend.
- Toda tela que carrega dados cobre os quatro estados: carregando, erro, vazio e sucesso.
- Alvos de toque de no mínimo 44px, coluna única, sem rolagem horizontal na página —
  tabelas largas rolam dentro do próprio contêiner.
