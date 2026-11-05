# Documentação do Sistema — SGI

## 1. Visão geral

O SGI (Sistema de Gestão de Investimentos) ajuda a registrar e acompanhar carteiras de investimentos, posições, preços, proventos, rentabilidade e informações para apoio à apuração de imposto de renda. É uma ferramenta gerencial e informativa; não presta consultoria nem recomendação de investimentos.

O sistema atende ativos brasileiros e internacionais, renda fixa privada, títulos públicos e criptoativos. Os recursos disponíveis incluem cadastro e movimentação de ativos, acompanhamento de posições, histórico patrimonial, proventos, eventos corporativos, indicadores e relatórios.

## 2. Integridade dos dados financeiros

- As transações persistidas formam o registro canônico das movimentações da carteira. Posições e custos são derivados delas, considerando a sequência cronológica dos eventos.
- Leituras financeiras usam dados já persistidos. A atualização de dados externos é realizada por rotinas próprias, separadas da leitura das telas.
- O sistema não deve inventar preços, taxas ou valores ausentes. Lacunas são apresentadas como pendências até que exista informação confiável.
- Snapshots patrimoniais e rentabilidade TWR são mantidos pelo fluxo canônico de consolidação. O snapshot oficial continua diário; não são criados snapshots oficiais intradiários.
- Acesso a informações de carteira depende da autenticação e da autorização do proprietário.

## 3. Atualização de cotações e snapshots

Os horários abaixo usam o fuso de Brasília. A disponibilidade e o horário efetivo de cada cotação dependem do calendário de negociação e dos provedores de dados.

| Rotina | Frequência | Escopo |
| --- | --- | --- |
| Cotações de mercado | De hora em hora, em dias úteis, das 09h às 18h | Ativos de mercado acompanhados, incluindo criptoativos |
| Cotações de cripto fora do pregão | De hora em hora, fora da janela acima e aos fins de semana | Criptoativos, que negociam continuamente |
| Snapshot patrimonial oficial e manutenção TWR | Diariamente, às 21h, inclusive sábados, domingos e feriados | Consolidação com cotações persistidas na data; ativos sem negociação usam o último dado disponível |

As atualizações de preços podem invalidar dados derivados para que sejam recalculados com as cotações disponíveis. A rotina de snapshot diário não substitui as transações e não cria movimentações financeiras.

## 4. Fontes de dados

O SGI integra provedores de mercado e fontes públicas para cotações, séries econômicas, proventos e informações de títulos públicos. A cobertura varia por classe de ativo e período. Dados sem cobertura suficiente permanecem identificados como indisponíveis ou pendentes, em vez de serem completados por estimativas não verificadas.

## 5. Segurança e acesso

O sistema requer autenticação para recursos protegidos e verifica a autorização para acesso às carteiras. Os recursos de autenticação incluem tokens de sessão e suporte a segundo fator. Segredos e credenciais de ambiente são configurados fora da documentação e não devem ser incluídos em arquivos versionados.

Solicitações de recuperação de senha são limitadas por conta: duas solicitações em uma janela de dois minutos; uma terceira solicitação bloqueia novos envios por 60 minutos. O limite usa Redis em produção e falha de forma fechada se Redis não estiver disponível. Fora de produção, há fallback em memória para desenvolvimento e testes. Um SuperAdmin pode remover os bloqueios de login e de recuperação pela ação **Desbloquear usuário** no painel administrativo; a operação fica registrada na auditoria.

## 6. Governança e Integridade Operacional

- O sistema adota padrões rigorosos de integridade de dados e validação prévia de operações financeiras.
- As rotinas de cálculo são determinísticas e passam por verificações automáticas contínuas de consistência.
- Registros contábeis e históricos de transações são auditáveis e protegidos contra modificações extemporâneas sem lastro.
- O ambiente operacional conta com isolamento lógico de contas e monitoramento ininterrupto de disponibilidade dos serviços.

## 7. Central de ajuda

A rota protegida `/carteira/ajuda`, acessível pelo menu do usuário no topo da
aplicação, reúne perguntas e respostas sobre navegação, operações, dados,
rentabilidade, ferramentas, IRPF e segurança. É possível pesquisar por texto e
filtrar por categoria; os atalhos levam às páginas correspondentes. O assistente
documental consulta um conjunto explícito de manuais funcionais, retorna trechos
com título e seção de origem e não lê dados da carteira nem grava conversas. A
rota `/api/v1/help/ask` exige autenticação, aceita perguntas de 3 a 500
caracteres e limita a 10 consultas por minuto por endereço de origem. Quando a
documentação não contém evidência suficiente, informa que não encontrou resposta.

O assistente documental atua como suporte à navegação e esclarecimento de regras funcionais. O assistente de Análise continua separado e responde
sobre alocação, riscos e proventos da carteira selecionada.

A IA disponível em Análise usa as métricas determinísticas e não responde sobre
o conteúdo completo da documentação.

## 8. Guias relacionados

- [Guia do backend](../backend/README.md)
- [Guia do frontend](../frontend/README.md)
- [Execução assíncrona confiável](RELIABLE_ASYNC.md)
- [Runbook de certificação de dados reais](REAL_DATA_CERTIFICATION_RUNBOOK.md)
