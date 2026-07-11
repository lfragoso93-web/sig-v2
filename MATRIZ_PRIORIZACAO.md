# Matriz de Priorização — SGI v2

**Atualizada em:** 11 de julho de 2026

Esta matriz substitui a versão de 2 de julho de 2026. As entregas de consolidação financeira, importação CSV, administração de usuários e correções do Resumo já foram concluídas e validadas.

---

## Critérios

| Critério | Pergunta |
|---|---|
| Impacto | Quanto a entrega melhora segurança, resiliência ou valor ao usuário? |
| Urgência | Existe risco imediato ou bloqueio para outras entregas? |
| Esforço | Qual o tamanho técnico e operacional? |
| Dependência | A entrega habilita ou depende de outro bloco? |
| Risco | Qual a probabilidade de regressão ou incidente? |

---

## Prioridades atuais

| Ordem | Issue | Entrega | Impacto | Esforço | Risco | Decisão |
|---|---:|---|---|---|---|---|
| 1 | #80 | Compliance de documentação e API pública | Alto | Baixo-médio | Baixo | Executar agora |
| 2 | #83 | Backup seguro — primeira fase | Muito alto | Médio | Médio | Próxima entrega |
| 3 | #97 | Google OAuth | Alto | Médio | Médio-alto | Após backup |
| 4 | #90 | Refinamento da página Patrimônio | Médio | Médio | Baixo-médio | Após infraestrutura |
| 5 | #57 | Análise de Carteira | Alto | Alto | Médio | Próximo módulo de produto |
| 6 | #58 | Janela Global do Ativo | Alto | Médio-alto | Médio | Pode compartilhar contratos com análise |
| 7 | #56 | Motor e relatórios de IRPF | Muito alto | Alto | Alto | Iniciar após especificação fiscal |

---

## Quadrantes impacto versus esforço

### Ganhos rápidos

- #80 — compliance.
- Testes específicos do fallback de preços do Tesouro Direto.
- Testes de reexecução do pipeline de proventos.
- Documentação operacional de backup.

### Alto impacto e esforço controlado

- Primeira fase de backup da #83.
- Google OAuth #97.
- Refinamento de Patrimônio #90.

### Investimentos estratégicos

- Análise de Carteira #57.
- Janela Global do Ativo #58.
- IRPF #56.

### Evitar neste momento

- Restore direto em produção sem modo de manutenção.
- Recomendações financeiras subjetivas antes do módulo analítico básico.
- Exportações fiscais antes de existir motor de apuração testado.
- Novos KPIs paralelos aos contratos financeiros canônicos.

---

## Sequência recomendada

### Ciclo 1 — Compliance

- Documentos públicos.
- OpenAPI, schemas e respostas.
- Configuração compatível.
- Testes de regressão.
- PR para `main`.

### Ciclo 2 — Resiliência

- Serviço de backup.
- Checksum e retenção.
- Lock e auditoria.
- Download autenticado.
- Restore manual em ambiente isolado.

### Ciclo 3 — Identidade

- Modelo de identidade externa.
- Login e vínculo seguro.
- Callback frontend.
- Testes de segurança.

### Ciclo 4 — Experiência

- Reorganização da página Patrimônio.
- Responsividade.
- Estados vazios e falhas parciais.

### Ciclo 5 — Produto

- Análise de Carteira.
- Janela Global do Ativo.
- Motor fiscal e IRPF.

---

## Matriz de riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Renomear configuração e quebrar ambiente | Média | Alto | Compatibilidade e depreciação gradual |
| Backup conter dados sensíveis | Alta | Alto | Acesso restrito, armazenamento temporário e auditoria |
| Restore interromper o sistema | Alta | Muito alto | Manter fora da primeira fase |
| Vinculação OAuth incorreta | Média | Muito alto | E-mail verificado, identidade externa e testes |
| Divergência de KPIs reaparecer | Baixa-média | Alto | Reutilizar contratos canônicos |
| Motor fiscal produzir cálculo incorreto | Média | Muito alto | Especificação formal e testes extensivos |

---

## Definição de sucesso do ciclo atual

### Compliance #80

- Zero nomes de fornecedores nos documentos públicos selecionados.
- OpenAPI e respostas públicas com termos genéricos.
- Configuração atual preservada.
- Testes automatizados contra regressão.

### Backup #83 — fase 1

- Superadmin gera e baixa backup válido.
- Arquivo possui checksum e expiração.
- Execuções concorrentes são bloqueadas.
- Operação fica registrada em auditoria.
- Restore manual em ambiente isolado é bem-sucedido.

### OAuth #97

- Login social não quebra o fluxo atual.
- Contas são vinculadas sem takeover.
- Cenários de erro são cobertos.

---

## Processo

- Desenvolvimento na `stable-15jun`.
- Commits pequenos e temáticos.
- Validação antes de cada PR.
- Documentação atualizada junto da entrega.
- Merge em `main` apenas após bloco estável.
