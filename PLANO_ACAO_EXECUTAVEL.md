# Plano de Ação Executável — SGI v2

**Atualizado em:** 11 de julho de 2026  
**Branch de desenvolvimento:** `stable-15jun`

Este plano substitui o roteiro criado em 2 de julho de 2026. Desde então, foram concluídos e validados os blocos de consolidação financeira, importação CSV, administração de usuários, integridade de carteiras e correções da página Resumo.

---

## Objetivo do ciclo atual

Concluir a estabilização operacional e preparar o sistema para novas funcionalidades sem reabrir divergências nos contratos financeiros.

### Regras de execução

1. Trabalhar sempre na `stable-15jun`.
2. Dividir mudanças em commits pequenos.
3. Não misturar compliance, infraestrutura e novas funcionalidades na mesma entrega.
4. Adicionar testes proporcionais ao risco.
5. Atualizar README, roadmap e changelog antes da PR para `main`.

---

## Bloco 1 — Compliance da documentação e API pública — #80

**Status:** Em andamento  
**Objetivo:** remover detalhes de fornecedores das superfícies públicas sem quebrar integrações existentes.

### Etapa 1.1 — Documentação principal

- [x] Revisar README.
- [x] Revisar CHANGELOG.
- [x] Revisar ROADMAP.
- [x] Atualizar documentos de gaps e planejamento desatualizados.
- [ ] Revisar documentos auxiliares restantes.

### Etapa 1.2 — OpenAPI e respostas públicas

- [ ] Revisar títulos, descrições e exemplos dos endpoints.
- [ ] Substituir identificadores de fornecedor em campos públicos por valores genéricos.
- [ ] Garantir que exceções retornadas ao cliente não incluam detalhes internos.
- [ ] Manter nomes técnicos apenas em logs internos e módulos de integração.

### Etapa 1.3 — Configuração

- [ ] Preservar variáveis atuais para evitar quebra de ambientes.
- [ ] Introduzir aliases genéricos quando necessário.
- [ ] Documentar depreciação antes de remover qualquer nome legado.

### Etapa 1.4 — Regressão

- [ ] Adicionar teste de varredura dos documentos públicos.
- [ ] Adicionar teste da descrição OpenAPI e schemas expostos.
- [ ] Executar testes backend e build do frontend.

### Critério de aceite

- Nenhum nome de fornecedor em documentos públicos.
- OpenAPI e respostas públicas com terminologia genérica.
- Configurações existentes continuam funcionando.
- Testes de compliance passam em CI.

---

## Bloco 2 — Backup seguro — primeira fase da #83

**Status:** Próximo  
**Objetivo:** permitir geração de backup sem introduzir o risco operacional do restore direto.

### Etapa 2.1 — Serviço de backup

- [ ] Criar serviço dedicado para geração de dump comprimido.
- [ ] Usar arquivo temporário fora de diretórios públicos.
- [ ] Calcular checksum SHA-256.
- [ ] Definir nome com timestamp e identificador da aplicação.
- [ ] Remover arquivos expirados automaticamente.

### Etapa 2.2 — Segurança

- [ ] Restringir a superadmin.
- [ ] Adicionar lock contra execuções simultâneas.
- [ ] Registrar início, sucesso e falha em auditoria.
- [ ] Não retornar comandos, credenciais ou paths internos ao frontend.

### Etapa 2.3 — API e frontend

- [ ] Criar endpoint autenticado para download.
- [ ] Exibir estado de processamento.
- [ ] Apresentar checksum e data do backup.
- [ ] Tratar falhas com mensagens operacionais genéricas.

### Etapa 2.4 — Validação

- [ ] Testar geração do arquivo.
- [ ] Restaurar manualmente em banco isolado.
- [ ] Comparar migrations, tabelas e registros essenciais.
- [ ] Documentar procedimento de recuperação.

### Fora de escopo

O restore pela aplicação será tratado em uma issue/fase separada após definição de modo de manutenção, reautenticação forte, backup pré-restore, validação de versão e rollback.

---

## Bloco 3 — Google OAuth — #97

**Status:** Planejado

### Backend

- [ ] Criar modelo de identidade externa.
- [ ] Adicionar migration.
- [ ] Validar token e e-mail verificado.
- [ ] Implementar vínculo seguro com conta existente.
- [ ] Definir política de cadastro automático.
- [ ] Preservar login por e-mail e senha.

### Frontend

- [ ] Adicionar botão de login.
- [ ] Implementar callback.
- [ ] Tratar conflito, cancelamento e falha.
- [ ] Manter o fluxo atual como alternativa.

### Testes

- [ ] Novo usuário.
- [ ] Conta existente com vínculo permitido.
- [ ] E-mail não verificado.
- [ ] Conflito de identidade.
- [ ] Token inválido ou expirado.

---

## Bloco 4 — Refinamento de Patrimônio — #90

**Status:** Planejado

- [ ] Separar composição, metas, concentração e posições.
- [ ] Melhorar hierarquia visual e responsividade.
- [ ] Preservar os contratos canônicos de KPIs.
- [ ] Cobrir estados vazios e cotações parciais.
- [ ] Adicionar testes de renderização para layouts principais.

---

## Bloco 5 — Novos módulos de produto

### Análise de Carteira — #57

- [ ] Concentração por ativo e classe.
- [ ] Comparação com metas.
- [ ] Alertas objetivos.
- [ ] Rebalanceamento por novos aportes.

### Janela Global do Ativo — #58

- [ ] Consolidar o drawer existente.
- [ ] Histórico de preços e proventos.
- [ ] Posição, custo médio e resultado.
- [ ] Indicadores derivados.

### IRPF — #56

- [ ] Especificar regras fiscais.
- [ ] Implementar motor de apuração independente.
- [ ] Cobrir operações e eventos por testes.
- [ ] Adicionar fechamento mensal/anual.
- [ ] Implementar relatórios e exportações.

---

## Checklist de cada entrega

### Antes de implementar

- [ ] Confirmar issue e critérios de aceite.
- [ ] Confirmar que a `stable-15jun` está sincronizada com `main`.
- [ ] Identificar dependências e riscos.

### Durante a implementação

- [ ] Criar commits pequenos e temáticos.
- [ ] Adicionar testes.
- [ ] Não misturar escopos independentes.

### Antes da PR

- [ ] Executar testes backend relevantes.
- [ ] Executar testes, typecheck e build do frontend quando aplicável.
- [ ] Validar fluxo funcional.
- [ ] Atualizar documentação.
- [ ] Abrir PR da `stable-15jun` para `main` com impacto e validação.
