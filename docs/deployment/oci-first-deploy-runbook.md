# SGI v2 OCI First Deploy / Homologation Runbook

Status: OCI e alvo de homologacao de SHA previamente certificado localmente.

Atualizado em 10/09/2026.

Target preferencial:

- Shape: `VM.Standard.A1.Flex` quando houver capacidade;
- perfil inicial historico: `1 OCPU / 6 GB`, ajustavel dentro dos guardrails Free Tier;
- Boot volume: `80 GB`;
- OS: Ubuntu ARM64;
- App directory: `/opt/sgi-v2`;
- Network entrypoint: Cloudflare Tunnel only.

E2 Micro pode ser usado como lab limitado, mas nao substitui a homologacao de capacidade/performance do alvo final.

## 0. Precondition — Certified Candidate

Antes do deploy:

- branch de desenvolvimento: `stable-15jun`;
- codigo e testes pesados executados localmente;
- SHA candidato registrado;
- nenhuma correcao deve ser feita diretamente na VM;
- enquanto `ready_for_real_data=false`, usar apenas dados permitidos pelo estagio vigente.

Se a OCI revelar defeito de codigo, interromper, reproduzir/corrigir localmente, publicar novo SHA e repetir a homologacao.

## 1. Post-Boot Baseline Checks

```bash
cloud-init status --wait
cloud-init status --long
docker --version
docker compose version
sudo systemctl status docker --no-pager
sudo ufw status verbose
ls -ld /opt/sgi-v2
```

Ou:

```bash
cd /opt/sgi-v2
sh scripts/oci_vm_baseline_check.sh
```

NO-GO se Docker estiver ausente, firewall permitir ingress publico indevido ou `/opt/sgi-v2` estiver inconsistente.

## 2. Deployment Source — Exact SHA

Nao fazer deploy apenas do "HEAD atual" da branch. Fazer checkout do SHA certificado.

```bash
cd /opt
git clone --branch stable-15jun <repo-url> sgi-v2
cd /opt/sgi-v2
git fetch origin
git reset --hard <CERTIFIED_SHA>
DEPLOYED_SHA="$(git rev-parse HEAD)"
printf 'DEPLOYED_SHA=%s\n' "$DEPLOYED_SHA"
```

Esperado:

```text
DEPLOYED_SHA == CERTIFIED_SHA
```

Se diferir: NO-GO.

Nao editar arquivos versionados na VM para corrigir comportamento.

## 3. VM-Local Environment

```bash
cd /opt/sgi-v2
cp .env.oci.example .env
chmod 600 .env
```

Preencher somente na VM:

- `APP_COMMIT_SHA=<CERTIFIED_SHA>`;
- credenciais PostgreSQL;
- `SECRET_KEY`;
- `CORS_ORIGINS`;
- SuperAdmin;
- tokens de providers quando autorizados;
- `CLOUDFLARE_TUNNEL_TOKEN`.

O valor de `APP_COMMIT_SHA` deve ser comparado com `git rev-parse HEAD` antes do start.

Nunca registrar segredos em Git, Issues ou logs.

Executar:

```bash
sh scripts/oci_env_preflight.sh .env
```

## 4. Readiness Policy Before Start

Nao forcar flags para transformar um ambiente `GO_ASSISTED` em ambiente real-ready.

Enquanto #227 nao emitir GO:

```text
test_ready=true
GO_ASSISTED permitido quando o gate reportar isso
ready_for_real_data=false
/ready pode retornar 503
```

`/health=200` e o sinal de saude do processo para smoke de infraestrutura. `/ready=503` durante esta fase e comportamento esperado, nao falha a ser contornada.

## 5. Render Compose Before Start

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml config > /tmp/sgi-compose-rendered.yml
grep -n "published:" /tmp/sgi-compose-rendered.yml || true
grep -n "cloudflared:" /tmp/sgi-compose-rendered.yml
```

NO-GO se backend/frontend publicarem host ports ou se o tunnel esperado estiver ausente.

## 6. Build And Start

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
```

Depois:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=100
```

Em VM pequena, manter perfil de workers conservador.

## 7. Local Container Health Checks

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec backend curl -f http://localhost:8000/health
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec db pg_isready -U "${POSTGRES_USER:-sgi}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec redis redis-cli ping
```

Esperado: backend saudavel, Postgres ready e Redis `PONG`.

Quando aplicavel, registrar separadamente `/ready`; nao exigir 200 enquanto o gate de dados reais estiver fechado.

## 8. Tunnel Check

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs cloudflared --tail=100
```

Esperado: tunnel conectado, hostname publico chegando ao frontend e `/api` roteado internamente.

Nunca abrir OCI `80/443` para contornar falha de tunnel. Nunca expor backend/Postgres/Redis.

## 9. Homologation Evidence

Registrar para o SHA implantado:

- `git rev-parse HEAD` e `APP_COMMIT_SHA`;
- estado de migrations;
- `/health`;
- `/ready` e motivo do estado;
- `user-test-readiness.v1` quando aplicavel;
- restart do stack/VM;
- persistencia dos volumes;
- CPU/RAM/disco;
- tunnel/hostname;
- portas publicadas.

Nao reexecutar suite pesada de desenvolvimento na OCI apenas para duplicar evidencia local. Executar apenas testes/smokes necessarios para provar a homologacao do ambiente.

## 10. Data Policy

Durante `GO_ASSISTED`, usar massa controlada. Restore/importacao real ampla, seed global real e contracoes destrutivas dependem da cadeia #226 -> #216 -> #158 -> #227.

Nao promover `ready_for_real_data` neste runbook.

## 11. Rollback

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml down
```

Preservar volumes salvo autorizacao explicita. Nunca executar `docker compose down -v` sem backup verificado e decisao operacional.