# Documenta��o do Sistema � SGI

> **Atualiza��o:** 1� de novembro de 2026
> **Produ��o:** OCI, publicada a partir da branch `main` ap�s merge de PR e deploy automatizado por GitHub Actions.
> **Desenvolvimento:** ambiente Windows local, branch `stable-15jun`.

## 1. Vis�o geral

O SGI (Sistema de Gest�o de Investimentos) ajuda a registrar e acompanhar carteiras de investimentos, posi��es, pre�os, proventos, rentabilidade e informa��es para apoio � apura��o de imposto de renda. � uma ferramenta gerencial e informativa; n�o presta consultoria nem recomenda��o de investimentos.

O sistema atende ativos brasileiros e internacionais, renda fixa privada, t�tulos p�blicos e criptoativos. Os recursos dispon�veis incluem cadastro e movimenta��o de ativos, acompanhamento de posi��es, hist�rico patrimonial, proventos, eventos corporativos, indicadores e relat�rios.

## 2. Integridade dos dados financeiros

- As transa��es persistidas formam o registro can�nico das movimenta��es da carteira. Posi��es e custos s�o derivados delas, considerando a sequ�ncia cronol�gica dos eventos.
- Leituras financeiras usam dados j� persistidos. A atualiza��o de dados externos � realizada por rotinas pr�prias, separadas da leitura das telas.
- O sistema n�o deve inventar pre�os, taxas ou valores ausentes. Lacunas s�o apresentadas como pend�ncias at� que exista informa��o confi�vel.
- Snapshots patrimoniais e rentabilidade TWR s�o mantidos pelo fluxo can�nico de consolida��o. O snapshot oficial continua di�rio; n�o s�o criados snapshots oficiais intradi�rios.
- Acesso a informa��es de carteira depende da autentica��o e da autoriza��o do propriet�rio.

## 3. Atualiza��o de cota��es e snapshots

Os hor�rios abaixo usam o fuso de Bras�lia. A disponibilidade e o hor�rio efetivo de cada cota��o dependem do calend�rio de negocia��o e dos provedores de dados.

| Rotina | Frequ�ncia | Escopo |
| --- | --- | --- |
| Cota��es de mercado | De hora em hora, em dias �teis, das 09h �s 18h | Ativos de mercado acompanhados, incluindo criptoativos |
| Cota��es de cripto fora do preg�o | De hora em hora, fora da janela acima e aos fins de semana | Criptoativos, que negociam continuamente |
| Snapshot patrimonial oficial e manuten��o TWR | Uma vez ao dia, �s 21h em dias �teis | Consolida��o di�ria das carteiras ap�s as rotinas de fechamento |

As atualiza��es de pre�os podem invalidar dados derivados para que sejam recalculados com as cota��es dispon�veis. A rotina de snapshot di�rio n�o substitui as transa��es e n�o cria movimenta��es financeiras.

## 4. Fontes de dados

O SGI integra provedores de mercado e fontes p�blicas para cota��es, s�ries econ�micas, proventos e informa��es de t�tulos p�blicos. A cobertura varia por classe de ativo e per�odo. Dados sem cobertura suficiente permanecem identificados como indispon�veis ou pendentes, em vez de serem completados por estimativas n�o verificadas.

## 5. Seguran�a e acesso

O sistema requer autentica��o para recursos protegidos e verifica a autoriza��o para acesso �s carteiras. Os recursos de autentica��o incluem tokens de sess�o e suporte a segundo fator. Segredos e credenciais de ambiente s�o configurados fora da documenta��o e n�o devem ser inclu�dos em arquivos versionados.

## 6. Desenvolvimento e publica��o

- O ambiente Windows local � usado para desenvolvimento na branch `stable-15jun`.
- A produ��o executa a vers�o integrada em `main`.
- Altera��es s�o validadas antes da publica��o, submetidas por Pull Request e integradas ap�s as verifica��es automatizadas exigidas pelo reposit�rio.
- O merge para `main` aciona o fluxo de CI/CD respons�vel pelo deploy em produ��o. A prontid�o do sistema depende tamb�m da valida��o de identidade e certifica��o correspondentes � vers�o implantada.
- Altera��es de banco de dados s�o versionadas por migra��es do Alembic e aplicadas pelo processo de publica��o da aplica��o.

## 7. Guias relacionados

- [Guia do backend](../backend/README.md)
- [Guia do frontend](../frontend/README.md)
- [Execu��o ass�ncrona confi�vel](RELIABLE_ASYNC.md)
- [Runbook de certifica��o de dados reais](REAL_DATA_CERTIFICATION_RUNBOOK.md)

