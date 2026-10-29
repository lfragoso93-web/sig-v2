# Runbook: Deploy Contínuo Automático no OCI via GitHub Actions (SSH)

> Objetivo: Operar a esteira de Continuous Deployment (CD) do GitHub Actions para o OCI sem consumir memória adicional na VM de produção.  
> Data: 29/10/2026  
> Escopo: CI/CD, GitHub Actions, SSH Action, Docker Compose

---

## 1. Visão Geral da Arquitetura

O deploy contínuo roda nos servidores do GitHub (`ubuntu-latest`) e conecta-se via SSH criptografado à instância do OCI somente no momento da atualização, consumindo **0 MB de RAM residente** na VM de produção.

### Vantagens da Abordagem (Opção 1):
- **Zero Consumo de RAM na VM:** Ideal para instâncias enxutas (`VM.Standard.E2.1.Micro`) ou dedicadas exclusivamente aos contêineres da aplicação.
- **Fail-Safe Gate:** O workflow `.github/workflows/deploy-oci.yml` só é disparado automaticamente quando a suíte completa de testes e segurança (`SIG v2 CI/CD`) é aprovada na branch `main`.
- **Segredos Criptografados no GitHub Vault:** As credenciais de conexão residem exclusivamente nos *Repository Secrets* do GitHub.

---

## 2. Segredos Configurados no GitHub Actions

Os seguintes segredos estão configurados em **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**:

| Secret | Descrição |
|---|---|
| `OCI_HOST` | IP público da instância OCI (`168.75.106.202`) |
| `OCI_USER` | Usuário do sistema operacional (`ubuntu`) |
| `OCI_SSH_PORT` | Porta SSH (`22`) |
| `OCI_SSH_KEY` | Chave privada SSH autorizada na instância |

Caso o IP ou a chave mudem no futuro, basta atualizar via GitHub CLI:
```powershell
gh secret set OCI_HOST --body "<NOVO_IP>"
Get-Content -Raw "caminho\para\chave.key" | gh secret set OCI_SSH_KEY
```

---

## 3. Como o Deploy Automático Funciona

1. Quando há um merge/push na `main` (e o workflow `SIG v2 CI/CD` conclui com sucesso), ou quando acionado manualmente via `workflow_dispatch`:
2. O job `Rebuild and Deploy on OCI via SSH` conecta na VM em `/opt/sig-v2` (ou `/opt/sgi-v2`).
3. Executa `git fetch` e `git pull --ff-only` da branch alvo.
4. Atualiza `APP_COMMIT_SHA` no arquivo `.env` com o hash exato do commit.
5. Executa `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build`.
6. Executa `sh scripts/oci_smoke_test.sh`, verificando:
   - `/health` respondendo HTTP 200;
   - PostgreSQL e Redis saudáveis (`pg_isready` e `PONG`);
   - Cloudflare Tunnel ativo e sem vazamento de credenciais;
   - Nenhuma porta interna exposta indevidamente no host.

---

## 4. Disparo Manual pelo GitHub

Para disparar o deploy de qualquer branch (`stable-15jun` ou `main`) manualmente pela interface web:
1. No GitHub, acesse a aba **Actions**.
2. Selecione **Deploy to OCI Production** no menu lateral esquerdo.
3. Clique em **Run workflow**, informe a branch desejada e confirme em **Run workflow**.
