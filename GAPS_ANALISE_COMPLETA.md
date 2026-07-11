# Análise Atual de Gaps — SGI v2

**Atualizado em:** 11 de julho de 2026  
**Branch de desenvolvimento:** `stable-15jun`

Este documento substitui a análise estática de 2 de julho de 2026. O estado do sistema mudou significativamente desde então: a consolidação financeira, a importação CSV, a administração de usuários, a auditoria básica e a estabilização do Resumo já foram entregues e validadas.

---

## Estado consolidado

### Entregas concluídas

- KPIs canônicos entre Resumo, Patrimônio e Rentabilidade.
- Evolução patrimonial diária e mensal.
- Importação CSV com modelo, preview, pré-validação e persistência.
- Isolamento de carteiras por usuário.
- Administração de usuários e proteção do último superadmin.
- Exclusão segura de carteiras com preservação de auditoria.
- Pipeline de proventos por carteira.
- Catálogo e preços de Tesouro Direto com fonte oficial secundária.
- Cobertura backend ampliada e testes frontend iniciais.

### Issues encerradas neste ciclo

- #124 — Correções da página Resumo.
- #98 — Administração de usuários.
- #82 — Importação CSV.

---

## Gaps ativos por prioridade

## 1. Compliance da documentação e API pública — #80

**Criticidade:** Alta  
**Esforço:** Baixo a médio  
**Status:** Em andamento

### Pendências

- Remover nomes explícitos de fornecedores dos documentos públicos.
- Usar terminologia genérica em OpenAPI, schemas e respostas públicas.
- Garantir que mensagens retornadas ao cliente não exponham detalhes das integrações.
- Preservar nomes técnicos somente em módulos internos e configuração compatível.
- Adicionar teste automatizado contra regressões documentais.

### Critério de aceite

- Documentação pública sem nomes de fornecedores externos.
- OpenAPI e respostas públicas usando identificadores genéricos.
- Configuração existente preservada ou migrada com compatibilidade.
- Teste de compliance executado em CI.

---

## 2. Backup seguro — primeira fase da #83

**Criticidade:** Alta  
**Esforço:** Médio  
**Status:** Planejado

### Escopo recomendado

- Geração de backup exclusiva para superadmin.
- Download autenticado do arquivo comprimido.
- Checksum do artefato.
- Lock contra execuções concorrentes.
- Auditoria da operação.
- Retenção e limpeza automática de arquivos temporários.
- Teste de restauração manual em ambiente isolado.

### Fora da primeira fase

O restore direto pela aplicação deve permanecer separado até existir modo de manutenção, reautenticação forte, backup pré-restore, validação de compatibilidade e rollback operacional.

---

## 3. Google OAuth — #97

**Criticidade:** Média-alta  
**Esforço:** Médio  
**Status:** Planejado

### Pendências

- Modelo de identidade externa.
- Fluxo Authorization Code com proteção adequada.
- Vínculo seguro com conta existente.
- Validação de e-mail verificado.
- Cadastro automático controlado.
- Testes de login, vínculo, conflito e erro.

---

## 4. Refinamento da página Patrimônio — #90

**Criticidade:** Média  
**Esforço:** Médio  
**Status:** Planejado

### Pendências

- Separar composição, metas, concentração e posições em cards claros.
- Melhorar responsividade sem duplicar KPIs.
- Preservar os contratos financeiros canônicos.
- Cobrir estados vazios e falhas parciais de cotação.

---

## 5. Análise de Carteira — #57

**Criticidade:** Média  
**Esforço:** Alto  
**Status:** Planejado

### MVP recomendado

- Concentração por ativo e classe.
- Comparação com metas.
- Score de diversificação.
- Alertas objetivos de concentração.
- Simulação de rebalanceamento por novos aportes.

---

## 6. Janela Global do Ativo — #58

**Criticidade:** Média  
**Esforço:** Médio-alto  
**Status:** Parcialmente estruturado

### Pendências

- Consolidar o drawer existente.
- Histórico de preços.
- Histórico de proventos.
- Posição, preço médio, valor atual e resultado.
- Indicadores derivados sem expor detalhes das fontes de dados.

---

## 7. IRPF — #56

**Criticidade:** Média-alta  
**Esforço:** Alto  
**Status:** Planejado

### Ordem recomendada

1. Especificação das regras fiscais.
2. Motor de apuração independente da interface.
3. Testes de custo médio, vendas, taxas, prejuízos e operações intradiárias.
4. Fechamento mensal e anual.
5. Relatórios e exportações.

---

## Débitos técnicos contínuos

- Ampliar testes de reexecução e indisponibilidade do pipeline de proventos.
- Adicionar testes do fallback de preços do Tesouro Direto.
- Expandir cobertura frontend e fluxos E2E.
- Revisar monitoramento e performance com dados de produção.
- Produzir documentação de arquitetura, deploy e troubleshooting.

---

## Ordem atual de execução

1. Concluir #80 — compliance.
2. Implementar backup seguro como primeira fase da #83.
3. Implementar #97 — Google OAuth.
4. Executar #90 — refinamento de Patrimônio.
5. Avançar em #57 e #58.
6. Estruturar o motor fiscal da #56.

---

## Processo de entrega

- Todo desenvolvimento ocorre na `stable-15jun`.
- Commits devem ser pequenos e isolados.
- Cada bloco deve incluir testes proporcionais ao risco.
- README, roadmap e changelog são atualizados na consolidação.
- A entrega estável é enviada em PR para `main`.
