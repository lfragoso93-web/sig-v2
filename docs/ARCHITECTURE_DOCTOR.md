# Architecture Doctor

O Architecture Doctor consolida identificadores estáveis para invariantes que
já são protegidos por gates do SGI. Ele não substitui `pytest`, Flake8, mypy,
Alembic ou os testes arquiteturais existentes: esses continuam sendo a fonte de
verdade e aparecem como evidência no catálogo.

## Escopo deste bloco

O catálogo inicial vive em `backend/app/doctor/catalog.py` e registra os IDs
`SGI001` a `SGI011`, título, severidade, tipo de check e arquivos que hoje
protegem cada regra. Os contratos em `backend/app/doctor/contracts.py` definem o
envelope de resultado e os códigos de saída, mas ainda não existe runner ou CLI.

Nenhum código deste bloco acessa banco, rede, provedor, variáveis de ambiente ou
executa writes. Checks de banco e runtime estão apenas classificados; um bloco
posterior deverá definir opt-in/contexto explícito antes de executá-los.

## Semântica de resultado

- `pass`: a evidência esperada foi obtida e a regra passou;
- `fail`: a regra foi executada e encontrou violação;
- `skip`: a regra não foi executada no contexto atual;
- `error`: a regra não conseguiu produzir resultado confiável.

Os códigos de saída reservados são:

- `0` (`OK`): nenhuma falha bloqueante;
- `1` (`FINDINGS`): pelo menos uma regra de severidade `error` falhou;
- `2` (`INTERNAL_ERROR`): erro de execução, ID desconhecido ou `skip` em regra
  bloqueante.

Falhas e skips de severidade `warning` são informativos e não mudam o código de
saída. O catálogo inicial usa somente severidade `error`; `warning` fica
reservado para checks consultivos futuros. A ausência de evidência para regra
bloqueante nunca é promovida a sucesso.

## Mapa inicial

| ID | Domínio | Tipo | Evidência atual |
| --- | --- | --- | --- |
| SGI001 | Alembic/MetaData | database | drift gate e integridade de revisions |
| SGI002 | ORM/imports legados | static | guards de schema e consumidores removidos |
| SGI003 | writer de transações | behavioral | testes do writer canônico |
| SGI004 | writer de snapshots | static | política de writer único |
| SGI005 | dividendos por ativo | static | ausência de relações/materialização legadas |
| SGI006 | eventos corporativos | behavioral | plano e writer de reconciliação fail-closed |
| SGI007 | fronteiras DB-first | static | FX e preços de TWR |
| SGI008 | idempotência do bootstrap | behavioral | gates de reexecução do bootstrap |
| SGI009 | consumidores removidos | static | guards de tooling/modelos removidos |
| SGI010 | readiness | behavioral | contratos de sistema e teste assistido |
| SGI011 | identidade do runtime | runtime | SHA do Compose e execução do bootstrap |

Adicionar um ID não autoriza executar o respectivo gate. O runner futuro deve
declarar quais tipos de check suporta, preservar o comportamento fail-closed e
continuar read-only por padrão.
