# Runbook: GitHub Actions Self-Hosted Runner no OCI

> Objetivo: Configurar e operar o GitHub Actions Self-Hosted Runner na VM do OCI para deploy e rebuild automático contínuo a cada atualização na branch `main`.  
> Data: 29/10/2026  
> Escopo: CI/CD, OCI Always Free (Ubuntu ARM64 / x86_64), Docker Compose

---

## 1. Visão Geral da Arquitetura

O Self-Hosted Runner roda como um serviço de sistema (`systemd`) dentro da VM do OCI.

### Vantagens de Segurança:
- **Zero Portas Ingress Expostas:** O runner realiza chamadas de saída (*outbound HTTPS*) para o GitHub Actions através da porta 443. Não é necessário abrir a porta SSH (22) ou qualquer outra porta pública na Security List da VCN do OCI.
- **Isolamento de Segredos:** O arquivo `.env` com senhas de produção permanece restrito à VM em `/opt/sgi-v2/.env`, sem necessidade de replicar senhas no GitHub Secrets.
- **Fail-Safe Gate:** O workflow `.github/workflows/deploy-oci.yml` só é disparado se a suíte de testes de qualidade, linters e scans de segurança do `SIG v2 CI/CD` tiver passado com 100% de sucesso na branch `main`.

---

## 2. Pré-requisitos na VM do OCI

Conecte na VM via SSH (ou Console Cloudflare) e execute os passos preparatórios:

```bash
# 1. Garantir que o usuário atual tem acesso ao Docker sem sudo (ex.: ubuntu ou opc)
sudo usermod -aG docker $USER

# 2. Garantir permissões de escrita e ownership no diretório da aplicação
sudo chown -R $USER:$USER /opt/sgi-v2

# 3. Aplicar novo grupo na sessão atual (ou reconectar ao SSH)
newgrp docker
```

---

## 3. Instalação do Runner na VM

### Passo 3.1: Obter o Token de Registro no GitHub
1. No repositório GitHub (`lfragoso93-web/sig-v2`), acesse:  
   **Settings** $\rightarrow$ **Actions** $\rightarrow$ **Runners** $\rightarrow$ **New self-hosted runner**.
2. Selecione:
   - **Runner image:** Linux
   - **Architecture:** ARM64 (para instâncias `VM.Standard.A1.Flex`) ou x64 (para `VM.Standard.E2.1.Micro`).

### Passo 3.2: Download e Extração (Exemplo ARM64)
```bash
# Crie um diretório dedicado para o runner na home do usuário
mkdir -p ~/actions-runner && cd ~/actions-runner

# Baixe a versão mais recente do runner (verifique a URL exata indicada na página do GitHub)
# Exemplo para ARM64:
curl -o actions-runner-linux-arm64.tar.gz -L https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-arm64-2.321.0.tar.gz

# Extraia o pacote
tar xzf actions-runner-linux-arm64.tar.gz
```

### Passo 3.3: Configurar o Runner
Execute o script de configuração fornecido pelo GitHub com o token gerado:
```bash
./config.sh --url https://github.com/lfragoso93-web/sig-v2 --token <SEU_TOKEN_DO_GITHUB>
```
* Ao solicitar o nome do runner: Pressione Enter (usará o hostname da VM) ou digite `oci-sgi-prod`.
* Ao solicitar labels adicionais: Pode deixar padrão (`self-hosted,Linux,ARM64`).
* Ao solicitar a pasta de trabalho: Pressione Enter (usará `_work`).

---

## 4. Instalar como Serviço Contínuo (`systemd`)

Para garantir que o runner inicie automaticamente caso a VM do OCI seja reiniciada ou atualizada:

```bash
# Instalar o serviço systemd
sudo ./svc.sh install

# Iniciar o serviço
sudo ./svc.sh start

# Verificar status ativo
sudo ./svc.sh status
```

O status deverá exibir `Active: active (running)`.

---

## 5. Como o Deploy Automático Funciona

Assim que um Pull Request for aprovado e mergeado na branch `main`:

1. O workflow `SIG v2 CI/CD` executa os testes automatizados (pytest, vitest, migrations, scans).
2. Ao concluir com sucesso, o GitHub aciona automaticamente `.github/workflows/deploy-oci.yml`.
3. O runner na VM do OCI assume o job e executa:
   - `git fetch` e `git pull --ff-only origin main` em `/opt/sgi-v2`.
   - Atualiza `APP_COMMIT_SHA` no `.env` para refletir o commit exato.
   - Valida o ambiente com `scripts/oci_env_preflight.sh`.
   - Executa `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build`.
   - Executa `scripts/oci_smoke_test.sh` validando `/health=200` e nenhuma porta vazada.
4. O resultado completo dos logs fica visível diretamente na aba **Actions** do GitHub.

---

## 6. Disparo Manual (Se Necessário)

Se for necessário forçar um deploy ou rebuild sem esperar um push:
1. Vá na aba **Actions** no GitHub.
2. Selecione o workflow **Deploy to OCI Production (Self-Hosted)** à esquerda.
3. Clique em **Run workflow** $\rightarrow$ Escolha a branch desejada $\rightarrow$ Clique no botão verde **Run workflow**.

---

## 7. Comandos de Manutenção do Serviço

```bash
# Parar o serviço do runner
sudo ~/actions-runner/svc.sh stop

# Reiniciar o serviço
sudo ~/actions-runner/svc.sh restart

# Ver logs do serviço
journalctl -u actions.runner.* -f
```
