# Telas e navegação

## Fluxo entre as telas

```mermaid
stateDiagram-v2
    [*] --> Entrar

    Entrar: TelaEntrar
    note right of Entrar
        Login e cadastro na mesma tela.
        O guarda envia para cá quem não tem token.
    end note

    MinhasListas: TelaMinhasListas
    Editor: TelaEditorDeLista
    Resultado: TelaResultado
    Historico: TelaHistorico
    Mercados: TelaMercados

    Entrar --> MinhasListas: autenticado
    MinhasListas --> Editor: abrir ou criar lista
    MinhasListas --> Resultado: gerar recomendação
    MinhasListas --> Historico: ver histórico
    Editor --> Resultado: gerar recomendação
    Resultado --> Editor: voltar e ajustar a lista
    Resultado --> Historico: ver histórico
    Historico --> Resultado: voltar
    MinhasListas --> Mercados: menu
    Mercados --> MinhasListas: menu

    MinhasListas --> Entrar: sair ou token expirado
    Editor --> Entrar: token expirado
    Resultado --> Entrar: token expirado
```

Qualquer resposta `NAO_AUTENTICADO` limpa a sessão e devolve o usuário à tela de entrada,
preservando o destino em `?retorno=` para retomar de onde parou.

## Guarda de autenticação

```mermaid
flowchart TD
    A["Navegação para uma rota"] --> B{"rota tem meta.requerSessao?"}
    B -->|"Não"| C{"já está autenticado?"}
    C -->|"Sim, e a rota é /entrar"| D["Redireciona para as listas"]
    C -->|"Não"| E["Segue"]
    B -->|"Sim"| F{"tem token?"}
    F -->|"Sim"| E
    F -->|"Não"| G["Redireciona para /entrar<br/>com ?retorno=destino"]

    style G fill:#fdf6e3,stroke:#b8860b
```

A proteção é declarada em `meta.requerSessao` de cada rota, e não numa lista de exceções.
A diferença importa: uma tela nova nasce protegida se o autor marcar a meta, e o erro de
esquecer aparece como redirecionamento indevido — não como vazamento de dados.

## As telas

| Tela | Rota | Papel |
|---|---|---|
| `TelaEntrar` | `/entrar` | login e cadastro alternáveis no mesmo formulário |
| `TelaMinhasListas` | `/` | listas do usuário, criação e exclusão |
| `TelaEditorDeLista` | `/listas/:id` | montagem rápida da lista no celular |
| `TelaResultado` | `/listas/:id/resultado` | escolha do perfil e a recomendação |
| `TelaHistorico` | `/listas/:id/historico` | recomendações anteriores, imutáveis |
| `TelaMercados` | `/mercados` | supermercados considerados |

## Os quatro estados de cada tela

Toda tela que carrega dados passa por `EstadoDaTela`, que centraliza os estados. Sem esse
componente, cada tela precisaria repetir a mesma lógica — e a que esquecesse mostraria uma
tela branca.

```mermaid
flowchart LR
    A["Tela monta"] --> B["Carregando<br/>aria-live=polite"]
    B --> C{"Deu certo?"}
    C -->|"Não"| D["Erro<br/>mensagem + Tentar novamente"]
    C -->|"Sim"| E{"Veio algum dado?"}
    E -->|"Não"| F["Vazio<br/>explica o próximo passo"]
    E -->|"Sim"| G["Conteúdo"]
    D -->|"Tentar novamente"| B

    style D fill:#fdecea,stroke:#b3261e
    style F fill:#fdf6e3,stroke:#b8860b
    style G fill:#eaf5ee,stroke:#2f7a4d
```

O estado vazio nunca diz apenas "nada aqui": ele diz o que fazer em seguida — "crie a
primeira lista", "adicione itens antes de gerar a recomendação".

## Decisões de interface

### O seletor de perfil não fala de matemática

O usuário não sabe o que é peso multiobjetivo. Cada perfil se apresenta pelo efeito
prático:

| Perfil | Texto exibido |
|---|---|
| Econômico | "Menor preço possível, mesmo que precise visitar mais mercados." |
| Equilibrado | "Pondera o quanto se economiza contra o quanto se anda." |
| Conveniente | "Concentra a compra em poucos mercados, mesmo pagando um pouco mais." |

### Marca opcional, com "qualquer marca" como padrão

No editor de lista, o seletor de marca já vem em "Qualquer marca (costuma economizar
mais)". Fixar marca restringe os candidatos do otimizador e quase sempre encarece a
compra; deixar o padrão aberto orienta o usuário para a escolha que rende mais, sem tirar
dele a possibilidade de exigir uma marca específica.

### Gerar recomendação avisa que vai demorar

É a única operação lenta do sistema: percorre banco, monta payload e roda o solver. O botão
muda para "Calculando a melhor combinação…", fica desabilitado, e uma linha explica que
leva alguns segundos. Sem isso o usuário clica de novo achando que não funcionou.

### O resultado é um roteiro, não uma tabela de preços

A tela de resultado é organizada pela **ordem da rota**: primeira parada, o que comprar
ali, subtotal; segunda parada, e assim por diante. É a forma como a informação vai ser
usada de fato — com o celular na mão, dentro do mercado.

### Itens não atendidos aparecem, e em português

Um item que nenhum mercado pôde atender ganha seção própria, com o motivo traduzido:
`SEM_CANDIDATO` vira "nenhum mercado cadastrado vende este item" e
`SEM_CANDIDATO_COM_ESTOQUE` vira "os mercados têm o item, mas não na quantidade pedida".
Esconder essa informação faria o usuário chegar em casa sem perceber a falta.

### Busca de produto com atraso curto

Buscar a cada tecla geraria uma requisição por caractere. Um atraso de 300 ms agrupa a
digitação numa consulta só.

## Acessibilidade

- Todo campo tem `<label>` associado.
- Foco visível com `outline` de 3px, nunca removido.
- O resultado da recomendação está em região `aria-live="polite"`: quem usa leitor de tela
  é avisado quando ele chega.
- Tabelas com `<caption>`, `<th scope>` e `<tfoot>` para o subtotal.
- Botões de ação com `aria-label` quando o texto sozinho é ambíguo ("Excluir" repetido em
  várias linhas).
- A animação de carregamento respeita `prefers-reduced-motion`.
