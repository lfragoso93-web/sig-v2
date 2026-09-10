# SGI v2 OCI Execution Index

Status: homologacao de SHA certificado localmente.

Atualizado em 10/09/2026.

## Fronteira operacional obrigatoria

OCI nao e o ambiente de desenvolvimento nem o local primario de certificacao pesada do SGI v2.

Fluxo vigente:

1. desenvolver e corrigir localmente em `stable-15jun`;
2. executar certificacao pesada localmente com Docker/PowerShell;
3. fechar blockers P0/P1 e congelar um SHA candidato;
4. enviar exatamente esse SHA para OCI;
5. usar OCI para homologacao de deploy, migrations, persistencia, restart, recursos, rede, tunnel e smoke;
6. se OCI revelar falha de codigo/contrato, reproduzir e corrigir localmente, gerar novo SHA e homologar novamente;
7. nunca editar codigo na VM OCI como forma de correcao permanente.

`GO_ASSISTED` permite testes acompanhados e nao altera essa fronteira. `ready_for_real_data=false` permanece obrigatorio ate #226 -> #216 -> #158 -> #227.

## Phase 0. Freeze Candidate SHA

Antes de qualquer deploy OCI:

- confirmar branch `stable-15jun`;
- confirmar working tree local limpa;
- confirmar HEAD local = `origin/stable-15jun`;
- registrar SHA candidato;
- executar gates locais aplicaveis ao estagio;
- confirmar que nenhuma dependencia/toolchain nao relacionada foi misturada ao candidato.

Enquanto #303 ainda estiver em rodada assistida com P0/P1 em aberto, o SHA e apenas candidato, nao SHA de promocao.

## Phase 1. Prepare OCI Target

Use:

- `docs/deployment/oci-capacity-fallbacks.md`
- `docs/deployment/oci-micro-lab-runbook.md`
- `docs/deployment/oci-stack-retry-runbook.md`
- `docs/deployment/oci-cost-guardrails.md`
- `docs/deployment/oci.md`

A1 continua sendo o alvo preferencial quando houver capacidade. E2 Micro e laboratorio/homologacao limitada e nao e equivalente de performance.

Rejeitar recursos pagos nao autorizados.

## Phase 2. Validate VM Baseline

Use:

- `docs/deployment/oci-cloud-init.yaml`
- `docs/deployment/oci-vm-handoff-template.md`
- `docs/deployment/oci-first-deploy-runbook.md`
- `scripts/oci_vm_baseline_check.sh`

Validar cloud-init, Docker, firewall, volumes e `/opt/sgi-v2`.

## Phase 3. Deploy Exact Certified Source

Preferir Git e fazer checkout do SHA explicitamente registrado. Nao usar simplesmente o HEAD mais recente da branch se ele diferir do candidato certificado.

Exemplo conceitual:

```bash
cd /opt/sgi-v2
git fetch origin
git switch stable-15jun
git reset --hard <CERTIFIED_SHA>
git rev-parse HEAD
```

O SHA retornado deve ser identico ao SHA certificado localmente e ao `APP_COMMIT_SHA` do ambiente.

Nao desenvolver nem corrigir codigo na VM.

## Phase 4. Configure Environment

Use `.env.oci.example` e `scripts/oci_env_preflight.sh`.

- segredos somente na VM;
- `APP_COMMIT_SHA` deve corresponder ao checkout real;
- `ready_for_real_data` nao deve ser promovido manualmente;
- flags de bootstrap/seed devem respeitar o estagio autorizado.

## Phase 5. Data Policy

Enquanto o projeto estiver somente `GO_ASSISTED`:

- usar banco/dados de homologacao controlados;
- nao restaurar base real ampla;
- nao executar seed global real apenas para testar deploy;
- nao executar contracao destrutiva sem gate especifico.

Restore/importacao real pertencem aos gates #226/#216/#158/#227 e so entram no deploy de promocao quando formalmente autorizados.

## Phase 6. Start App

Use `docs/deployment/oci-first-deploy-runbook.md`.

Renderizar Compose, confirmar ausencia de host ports indevidos, executar migrations aprovadas e iniciar o stack.

## Phase 7. Publish Through Tunnel

Usar Cloudflare Tunnel para `http://frontend:80` e manter ingress OCI de aplicacao fechado.

Nunca expor `5432`, `6379` ou `8000` publicamente.

## Phase 8. Homologation Smoke

Validar:

- `/health` operacional;
- Postgres e Redis;
- tunnel/hostname;
- migrations no estado esperado;
- restart do stack/VM;
- persistencia dos volumes;
- CPU, RAM e disco;
- ausencia de portas publicas indevidas.

### Semantica de `/ready`

`/ready=503` e **esperado** enquanto `ready_for_real_data=false`. Isso nao invalida `GO_ASSISTED` nem um smoke de infraestrutura.

Para homologacao assistida, a combinacao esperada e:

```text
/health = 200
/ready = 503
user-test-readiness.v1 = GO_ASSISTED
ready_for_real_data = false
```

Nao alterar readiness manualmente para fazer o smoke passar.

## Phase 9. Promotion Homologation

Somente depois de #303, #226, #216 e #158 fornecerem o SHA/dataset de promocao:

- homologar exatamente esse SHA na OCI;
- executar os smokes e gates de resiliencia/seguranca aplicaveis;
- entregar a evidencia a #227;
- #227 registra GO ou NO-GO;
- somente um GO formal pode autorizar avaliar `ready_for_real_data=true`.

## Phase 10. Operate And Recover

Use:

- `docs/deployment/oci-operations-runbook.md`
- `docs/deployment/oci-disaster-recovery-runbook.md`

Rollback deve preservar volumes e voltar para commit conhecido + backup verificado. Nunca usar `docker compose down -v` sem autorizacao e backup.
