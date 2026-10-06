# Architecture Doctor

O Architecture Doctor consolida identificadores estáveis para invariantes que
já são protegidos por gates do SGI. Ele não substitui `pytest`, Flake8, mypy,
Alembic ou os testes arquiteturais existentes: esses continuam sendo a fonte de
verdade e aparecem como evidência no catálogo.

## Escopo atual

O catálogo inicial vive em `backend/app/doctor/catalog.py` e registra os IDs
`SGI001` a `SGI012`, título, severidade, tipo de check e arquivos que hoje
protegem cada regra. Os contratos em `backend/app/doctor/contracts.py` definem o
envelope de resultado e os códigos de saída. A CLI canônica é exposta por
`python -m app.doctor`.

O runner de `backend/app/doctor/static_runner.py` aceita uma lista explícita de
IDs e executa apenas evidências de regras classificadas como
`static`. Cada evidência deve ser um arquivo `backend/tests/test_*.py` já
registrado no catálogo. O runner reutiliza esses testes como autoridade e chama
pytest com o cache desabilitado, sem criar uma implementação paralela da regra.

A CLI exige seleção explícita e continua limitada aos checks estáticos:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.doctor --check SGI004
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
```

`--check` pode ser repetido. A saída JSON usa o schema
`architecture-doctor.v1` e o processo devolve os códigos `0`, `1` ou `2`
definidos pelo contrato.

Quando mais de um ID estático é selecionado, o caminho verde usa um único
processo pytest e remove evidências duplicadas. Se esse lote falhar, o runner
repete os checks isoladamente para atribuir a falha ao finding correto. Uma
divergência em que o lote falha e todos os checks isolados passam resulta em
`INTERNAL_ERROR`, sem promover um resultado inconsistente a sucesso.

Os testes do runner incluem uma violação arquitetural artificial em diretório
temporário. O pytest real falha, o finding recebe status `fail` e o Doctor
devolve `FINDINGS` (`exit_code=1`). A fixture temporária não modifica o checkout
nem qualquer banco.

Nenhum código deste bloco acessa banco, rede, provedor ou executa writes da
aplicação. Checks behavioral, database e runtime são rejeitados antes da
execução; um bloco posterior deverá definir opt-in/contexto explícito antes de
considerá-los.

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
| SGI012 | Agent Skills | static | pacotes versionados, metadados e roteamento no README |

Adicionar um ID não autoriza executar o respectivo gate. Qualquer runner deve
declarar quais tipos de check suporta, preservar o comportamento fail-closed e
continuar read-only por padrão.

## Como adicionar um finding

1. Crie ou identifique primeiro o gate autoritativo. O Doctor deve orquestrar
   uma proteção existente, não reimplementar a regra arquitetural.
2. Reserve o próximo ID sequencial livre no formato `SGIxxx`. IDs publicados
   não podem ser reutilizados, renumerados ou ter seu significado trocado.
3. Registre em `backend/app/doctor/catalog.py` um título acionável, severidade,
   tipo e pelo menos uma evidência versionada no repositório.
4. Use severidade `error` quando a violação deve bloquear. `warning` é apenas
   consultivo e exige justificativa explícita na documentação.
5. Classifique o check como `static`, `behavioral`, `database` ou `runtime` de
   acordo com a dependência real. Não reduza a classificação para fazê-lo caber
   no runner básico.
6. Para execução pelo runner estático, todas as evidências devem ser arquivos
   `backend/tests/test_*.py`, read-only, determinísticos e sem banco, rede ou
   provedor. Outros tipos permanecem apenas catalogados até terem runner próprio
   com opt-in e fronteira documentada.
7. Atualize a tabela deste documento e os testes do catálogo, runner e CLI.
   Preserve os gates pytest originais durante qualquer consolidação.

Validação mínima do contrato do Doctor:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_architecture_doctor_catalog.py tests/test_architecture_doctor_static_runner.py tests/test_architecture_doctor_cli.py tests/test_architecture_doctor_module_entrypoint.py -q -p no:cacheprovider
..\.venv\Scripts\python.exe -m flake8 app/doctor app/cli/architecture_doctor.py tests/test_architecture_doctor_*.py --jobs=1
..\.venv\Scripts\python.exe -m mypy app
..\.venv\Scripts\python.exe -m compileall -q app/doctor app/cli/architecture_doctor.py
```

No Windows deste checkout, se o pytest falhar antes das asserções com
`WinError 5` ao preparar `tmp_path`, repita o teste em container Linux com a
raiz do repositório montada read-only. Não interprete o erro de ACL como finding
do Doctor.
