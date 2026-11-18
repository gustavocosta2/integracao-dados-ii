# Instruções do Repositório (`AGENTS.md`)

Este arquivo define as regras obrigatórias para qualquer agente ou pessoa colaborando neste repositório.

## 1. Fluxo de Branches e Git

1. **Origem obrigatória de branches:**
   - Toda nova branch deve ser criada **sempre a partir de `develop`** (atualizada com `origin/develop`).
   - Nunca crie branches a partir de `master` ou de outra branch de trabalho.

2. **Nomenclatura de branches:**
   - **Proibido** usar prefixos com nomes de modelos, ferramentas ou agentes de IA (ex.: `codex/`, `claude/`, `gemini/`, `gpt/`, `cursor/`, `antigravity/`, etc.).
   - **Proibido** usar emojis no nome da branch.
   - Use o padrão `<tipo>/<descricao-em-kebab-case>`, com os prefixos: `feat/`, `fix/`, `test/`, `docs/`, `refactor/`, `chore/` ou `style/` (ex.: `feat/simulador-sensores`, `fix/validacao-schema`).

3. **Pull Requests (PRs):**
   - Ao enviar uma nova branch local para o repositório remoto (`origin`), **abra obrigatoriamente um Pull Request apontando para `develop`**.
   - Nunca faça merge ou push direto na `master` a partir de branches de tarefa.

4. **Proteção da branch `master`:**
   - A branch `master` **só pode receber merge da branch `develop`**.

5. **Idioma:**
   - Toda mensagem de **commit** e todo **Pull Request** (título e descrição) devem ser escritos em **português brasileiro (pt-BR)**.

## 2. Padrão de Commits e Emojis

Todo commit deve seguir o formato:

```text
<emoji> <tipo>(<escopo-opcional>): <descrição curta no infinitivo em pt-BR>
```

- Letra minúscula após os dois pontos e sem ponto final na primeira linha (idealmente até 72 caracteres).
- Se precisar explicar o motivo ou detalhes, pule uma linha e adicione o corpo em pt-BR.

### Tabela oficial de emojis e tipos

Use exatamente o emoji correspondente a cada tipo (não invente outros emojis):

| Emoji | Tipo | Uso | Exemplo |
| :---: | :--- | :--- | :--- |
| ✨ | `feat` | Nova funcionalidade | `✨ feat(simulador): gerar leituras de sensores IoT` |
| 🐛 | `fix` | Correção de bug ou falha | `🐛 fix(bronze): tratar timestamp nulo na ingestao` |
| 🧪 | `test` | Testes e testes de regressão | `🧪 test(regressao): validar schema para leitura negativa` |
| 📚 | `docs` | Documentação, README, ADRs e diagramas | `📚 docs(adr): registrar escolha do formato Iceberg` |
| ♻️ | `refactor` | Reorganização interna sem mudar comportamento | `♻️ refactor(ingestao): extrair leitura de configuracao` |
| 🔧 | `chore` | Docker, dependências, configurações e CI | `🔧 chore(docker): configurar servico do MinIO` |
| 🎨 | `style` | Formatação e lint sem alterar lógica | `🎨 style(simulador): padronizar formatacao com ruff` |

## 3. Padrão de Pull Requests

- **Título do PR:** segue exatamente o padrão da linha de commit com emoji (`<emoji> <tipo>(<escopo-opcional>): <resumo em pt-BR>`).
- **Corpo do PR:** sem emojis, seguindo o template de [`.github/pull_request_template.md`](.github/pull_request_template.md):
  - `## O que foi feito`
  - `## Contexto / Motivo`
  - `## Como testar`
  - `## Checklist`

## 4. Qualidade e Testes

- **Testes de regressão obrigatórios:** após resolver qualquer bug ou falha, adicione ou atualize **testes de regressão** cobrindo o problema corrigido e execute a suíte de testes antes de abrir o PR.
