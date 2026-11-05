# Manual Geral do Sistema — SGI

O **SGI (Sistema de Gestão de Investimentos)** é uma plataforma completa e institucional voltada ao controle patrimonial, acompanhamento de rentabilidade real, proventos e apoio à conformidade fiscal de investidores.

---

## 1. Visão Geral da Plataforma

O SGI atua como a central unificada para gestão de múltiplos portfólios, oferecendo visibilidade consolidada de ativos no Brasil e no exterior.

A plataforma abrange:
- **Gestão Multicarteira**: Criação e administração de carteiras independentes (ex.: Previdência, FIIs, Investimentos Internacionais, Reserva de Emergência).
- **Cobertura Multiclasse de Ativos**: Ações Brasileiras, Fundos Imobiliários (FIIs), Tesouro Direto, Renda Fixa Privada, ETFs, Criptomoedas, BDRs e Ações Internacionais (cotadas em Dólar/USD).
- **Rentabilidade Ponderada no Tempo (TWR e MWR)**: Cálculo rigoroso que expurga distorções causadas por novos aportes e resgates.
- **Radar Fiscal e IRPF**: Apuração mensal de ganhos de capital, controle de limites de isenção, compensação de prejuízos acumulados e apuração de DARF.
- **Gestão por Metas e Rebalanceamento Inteligente**: Definição de alocações alvo estratégicas e cálculo de novos aportes para rebalanceamento patrimonial sem necessidade de venda de ativos.

---

## 2. Integridade dos Dados e Modelo do Livro-Razão

A precisão financeira do SGI baseia-se em princípios fundamentais de consistência contábil:

1. **Livro-Razão Canônico (Ledger)**: Todas as posições, custos médios e saldos patrimoniais são projeções matemáticas diretas das transações registradas cronologicamente. Nenhuma posição é editada arbitrariamente sem uma operação de lastro.
2. **Leituras Independentes de Provedores Externos**: As telas financeiras consultam exclusivamente os dados persistidos e consolidados no banco de dados, garantindo navegação instantânea e confiável.
3. **Princípio de Não Invenção de Cotações**: O SGI nunca estima ou inventa preços quando um ativo não possui negociação ou cobertura suficiente na data. Em caso de ausência temporária de cotação oficial, o sistema informa a cobertura parcial de forma transparente.
4. **Fechamento Diário Oficial**: A consolidação dos saldos e a apuração da rentabilidade diária ocorrem diariamente em rotina oficial às 21h, preservando a série histórica do investidor.

---

## 3. Cadência de Atualização de Cotações e Fechamento

Os horários abaixo utilizam o fuso horário oficial de Brasília (BRT):

| Rotina | Frequência | Abrangência |
| :--- | :--- | :--- |
| **Cotações de Mercado Aberto** | De hora em hora, em dias úteis, das 09h às 18h | Ativos negociados em bolsa (Ações, FIIs, BDRs, ETFs, Índices) |
| **Cotações de Criptoativos** | De hora em hora, 24 horas por dia, 7 dias por semana | Criptomoedas e ativos digitais com negociação contínua |
| **Snapshot Patrimonial Oficial** | Diariamente, às 21h (inclusive finais de semana e feriados) | Consolidação de fechamento da carteira, cálculo de TWR diário e acumulação |

---

## 4. Central de Ajuda e Assistente de Navegação

A Central de Ajuda (`/carteira/ajuda`) reúne artigos explicativos, guias passo a passo e perguntas frequentes sobre todas as áreas do sistema:
- **Busca Rápida**: Filtre tópicos por categorias ou termos de interesse.
- **Atalhos Diretos**: Cada guia inclui botões para abrir instantaneamente a página funcional correspondente.
- **Assistente Cognitivo**: Tira dúvidas em linguagem natural fundamentando-se estritamente na documentação oficial de regras e navegação do SGI.
- **Privacidade Assegurada**: O assistente de ajuda não tem acesso à sua custódia, saldos ou dados financeiros sigilosos.

---

## 5. Segurança da Conta e Governança

- **Autenticação em Dois Fatores (2FA / MFA via TOTP)**: Compatível com Google Authenticator, Microsoft Authenticator e apps padrão TOTP para máxima proteção no acesso.
- **Isolamento Total por Usuário**: Cada investidor possui acesso restrito às suas carteiras e informações pessoais.
- **Proteção contra Força Bruta**: Bloqueios progressivos e automáticos em caso de tentativas sucessivas de login incorreto ou solicitações abusivas de redefinição de senha.
- **Auditoria de Operações**: Rastreabilidade completa de todas as compras, vendas e proventos lançados no histórico.
