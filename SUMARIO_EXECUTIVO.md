# Sumário Executivo — SGI v2

**Atualizado em:** 11 de julho de 2026  
**Branch de desenvolvimento:** `stable-15jun`

---

## Situação atual

O SGI v2 possui uma base funcional consolidada para gestão de investimentos, com backend FastAPI, frontend React + TypeScript, PostgreSQL, Redis, jobs agendados e autenticação JWT.

O ciclo mais recente estabilizou os contratos financeiros e os fluxos operacionais mais visíveis ao usuário.

### Entregas consolidadas

- Resumo, Patrimônio e Rentabilidade usando KPIs canônicos.
- Evolução patrimonial diária e mensal.
- Variação diária separada da rentabilidade acumulada.
- Importação CSV com modelo, preview, pré-validação e persistência.
- Proventos vinculados à carteira selecionada.
- Histórico de proventos idempotente.
- Catálogo e preços de Tesouro Direto com fallback oficial.
- Administração de usuários e proteção do último superadmin.
- Exclusão segura de carteiras e preservação da auditoria.
- Cobertura backend ampliada e testes frontend iniciais.

### Issues concluídas no ciclo

- #124 — Correções da página Resumo.
- #98 — Administração de usuários.
- #82 — Importação CSV.

---

## Prioridade atual

### #80 — Compliance da documentação e API pública

A próxima entrega remove detalhes de fornecedores das superfícies públicas do sistema.

O trabalho está dividido em:

1. documentação principal;
2. documentos auxiliares;
3. OpenAPI, schemas e respostas públicas;
4. configuração com compatibilidade;
5. testes automatizados contra regressões.

A documentação principal e os documentos de planejamento já começaram a ser atualizados na `stable-15jun`.

---

## Próximas entregas

### 1. Backup seguro — primeira fase da #83

- geração de backup para superadmin;
- download autenticado;
- checksum;
- lock de concorrência;
- auditoria;
- retenção temporária;
- teste de restauração manual em ambiente isolado.

O restore direto pela aplicação não faz parte da primeira fase devido ao risco operacional.

### 2. Google OAuth — #97

- identidade externa;
- vínculo seguro com conta existente;
- preservação do login por senha;
- callback frontend;
- testes de conflito e segurança.

### 3. Refinamento da página Patrimônio — #90

- melhor hierarquia visual;
- separação entre composição, metas, concentração e posições;
- responsividade;
- preservação dos contratos financeiros canônicos.

### 4. Novos módulos de produto

- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Motor fiscal e IRPF — #56.

---

## Riscos principais

| Risco | Mitigação |
|---|---|
| Reintrodução de divergência entre KPIs | Reutilizar exclusivamente os contratos canônicos |
| Quebra de configuração ao genericizar nomes | Compatibilidade e depreciação gradual |
| Exposição de dados em backups | Acesso restrito, retenção curta e auditoria |
| Restore causar indisponibilidade | Manter fora da primeira fase |
| Vinculação OAuth insegura | Identidade externa e e-mail verificado |
| Erros em regras fiscais | Especificação e testes antes da interface |

---

## Processo de desenvolvimento

- Todo desenvolvimento ocorre na `stable-15jun`.
- Commits são pequenos e isolados.
- Testes e validação funcional antecedem a PR.
- README, roadmap e changelog são atualizados na consolidação.
- O merge em `main` ocorre apenas após a validação do bloco.

---

## Documentos de referência

| Documento | Finalidade |
|---|---|
| `README.md` | Visão geral e execução do projeto |
| `ROADMAP_SPRINTS.md` | Entregas concluídas e futuras |
| `CHANGELOG.md` | Histórico de alterações |
| `GAPS_ANALISE_COMPLETA.md` | Gaps ativos e ordem de atuação |
| `PLANO_ACAO_EXECUTAVEL.md` | Plano técnico de execução |
| `MATRIZ_PRIORIZACAO.md` | Impacto, esforço e riscos |
