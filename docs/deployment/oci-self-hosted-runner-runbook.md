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

1. Todo push em `main` inicia `SIG v2 CI/CD`, inclusive commits apenas de documentação.
2. Quando essa execução termina com sucesso e foi iniciada por `push` em `main`, `Deploy to OCI Production` conecta à VM via SSH. Execuções manuais do CI não iniciam deploy.
3. O deploy fixa a branch `main`, atualiza o checkout e exige que o HEAD corresponda ao SHA exato aprovado pela execução de CI. Alterações rastreadas locais interrompem o deploy; artefatos não versionados ficam preservados.
4. Compose usa o projeto `sig-v2` explicitamente, mesmo quando o diretório de entrada é um symlink, e atualiza `APP_COMMIT_SHA` no `.env`.
5. As imagens backend e frontend são construídas em sequência. Containers antigos não são removidos antes do rebuild; `up -d --no-deps` recria apenas os serviços da aplicação.
6. O deploy valida a saúde dos serviços e executa `sh scripts/oci_smoke_test.sh`, verificando:
   - `/health` respondendo HTTP 200;
   - PostgreSQL e Redis saudáveis (`pg_isready` e `PONG`);
   - Cloudflare Tunnel ativo e sem vazamento de credenciais;
   - Nenhuma porta interna exposta indevidamente no host.

---

## 4. Execuções manuais

A execução manual de `SIG v2 CI/CD` roda validações, mas não dispara deploy. Produção atualiza somente após um push em `main` cujo workflow de CI conclua com sucesso.

