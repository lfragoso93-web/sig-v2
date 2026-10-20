# Ferramentas de simulação

Atualizado em 18/10/2026.

As duas experiencias ficam agrupadas no menu lateral em **Ferramentas**:
**Calculadora** (`/carteira/ferramentas/rendimentos`) e **Simulador RF**
(`/carteira/ferramentas/renda-fixa`). O grupo expande automaticamente ao abrir
uma dessas rotas; os enderecos e o acesso protegido permanecem iguais.

## Calculadora de rendimentos — primeira entrega da #359

A rota protegida `/carteira/ferramentas/rendimentos` oferece projeção isolada
com aporte inicial, aporte mensal, taxa efetiva anual e prazo de 1 a 600 meses.
O cálculo é puro no frontend, não chama API, não persiste dados e não lê nem
altera a carteira selecionada.

Premissas exibidas na tela:

- a taxa anual informada é efetiva e constante durante todo o horizonte;
- a taxa mensal equivalente é `(1 + taxa_anual)^(1/12) - 1`;
- o aporte inicial entra no mês zero;
- em cada mês, o saldo rende primeiro e o aporte mensal entra no fim do mês;
- não se aplicam impostos, inflação, tarifas, volatilidade nem datas de aporte.

Recorrência implementada: `saldo_m = saldo_(m-1) * (1 + taxa_mensal) + aporte_mensal`.
O total aportado é `aporte_inicial + aporte_mensal * meses`; o rendimento
projetado é saldo final menos total aportado. O arredondamento ocorre somente
na apresentação monetária.

Os campos aceitam aporte de R$ 0 a R$ 1 bilhão, taxa efetiva anual acima de
-100% até 1.000% e prazo inteiro entre 1 e 600 meses. Esses limites evitam
valores inválidos e crescimento numérico sem limite na interface; não são
recomendação de investimento.

## Comparador de Renda Fixa - frente B da #359

A rota protegida `/carteira/ferramentas/renda-fixa` compara dois tipos de titulo e suas taxas efetivas anuais. O tratamento de IR e derivado automaticamente do tipo de produto; nao existe uma escolha manual de isencao. Para cada cenario, a interface mostra valor/rendimento bruto, aliquota e IR estimados, valor liquido e retorno liquido efetivo anual, alem da taxa equivalente do primeiro titulo para igualar o valor liquido do segundo. O simulador nao le carteira, contratos, precos ou benchmarks e nao grava dados.

Regra automatica aplicada pelo produto:

- Tributaveis pela tabela regressiva: CDB, RDB, LC, debenture comum, Letra Financeira e Outro.
- Isentos no enquadramento legal padrao: LCI, LCA, LIG, CRI, CRA e debenture incentivada.
- A isencao pressupoe que emissao e titular atendam aos requisitos legais. A classificacao no SGI nao substitui o informe da instituicao nem prepara ou transmite a declaracao de IRPF.
- Nos produtos tributaveis, a retencao e feita pela fonte pagadora; nao e gerada uma obrigacao de DARF no simulador.

Premissas implementadas:

- a taxa anual inserida e efetiva, constante e capitalizada por dias corridos com expoente `dias / 365`;
- o prazo vai de 30 a 36.500 dias; o limite inferior exclui a estimativa de IOF ate o 29o dia;
- IR e calculado somente sobre rendimento positivo: ate 180 dias (22,5%), 181 a 360 (20%), 361 a 720 (17,5%) e acima de 720 (15%);
- o valor liquido e o bruto final menos IR estimado; a taxa equivalente resolve a taxa bruta anual do primeiro titulo que produz o mesmo valor liquido no prazo dado;
- taxas efetivas anuais devem representar a oferta completa; o simulador nao coleta cotacoes ou taxas de mercado.

Nao se modelam taxas de custodia/distribuicao, cupons, amortizacoes, marcacao a mercado, variacao de CDI/IPCA/SELIC, risco de credito ou resgate antecipado. A simulacao e educacional e nao substitui o informe da instituicao financeira ou orientacao fiscal.

As aliquotas seguem a tabela de aplicacoes de renda fixa da [Instrucao Normativa RFB 1.585/2015, art. 46](https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=67494). O tratamento das rendas e titulos isentos consta no [Manual da Receita Federal sobre rendimentos do capital](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/preenchimento/manual-mir/rendimentos/rendimentos-do-capital) e nas [hipoteses de isencao da Lei 11.033/2004, art. 3](https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2004/lei/l11033compilado.htm). A retencao na fonte esta descrita pela [Receita Federal - IRRF](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos/IRRF). Fontes consultadas em 18/10/2026.

Testes focados: 31 testes frontend e 20 testes backend do contrato passaram; typecheck e build de producao passaram. Publicado no projeto `sig-v2` pelo Cloudflare Tunnel no commit `8391474917684caa4e92f30d8b7c00cdb7ac5a28`; a rota e o bundle publicos responderam 200. `/ready=503` permanece por identidade de certificacao anterior; nenhum evento foi promovido nesta entrega.
