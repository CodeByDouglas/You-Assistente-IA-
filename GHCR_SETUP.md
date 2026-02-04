# Guia de Configuração: GitHub Container Registry (GHCR)

Este guia explica como utilizar o workflow configurado em `.github/workflows/docker.yml` para buildar e publicar sua imagem Docker automaticamente.

## 1. Visão Geral

- **Toda vez que você fizer um push na branch `main`**, o GitHub Actions vai:
    1. Baixar seu código.
    2. Buildar a imagem Docker com seu `Dockerfile`.
    3. Publicar a imagem no GHCR (`ghcr.io/seu-usuario/seu-repo`).
- **Tags geradas**:
    - `:latest`: A versão mais recente.
    - `:sha-ccccccc`: Uma versão imutável ligada ao commit específico (7 primeiros caracteres do SHA).

## 2. Configurações Necessárias (Primeira vez)

### Habilitar visibilidade do pacote
Por padrão, a primeira vez que um pacote é criado, ele pode ser **Private**. Para permitir que seus servidores façam pull:
1. Vá até a página principal do seu repositório no GitHub.
2. Na barra lateral direita, procure por **Packages**. Clique no pacote criado (após o primeiro workflow rodar).
3. Vá em **Package Settings**.
4. Em **Change package visibility**, você pode mudar para **Public** (acesso livre) ou manter **Private** e gerenciar permissões (dar acesso de leitura para seu servidor).

## 3. Comandos de Uso

### Teste Local (Antes de subir)
Para garantir que o build vai funcionar:
```bash
docker build -t teste-local .
docker run --env-file .env -p 8000:8000 teste-local
```

### No Servidor (Deploy)

⚠️ **IMPORTANTE:** Para que o sistema funcione completo (com Evolution API, Redis, Postgres), você NÃO deve rodar apenas o container do Django isolado. Você precisa subir a stack completa.

1. **Copie os arquivos para o servidor**:
   Você vai precisar levar dois arquivos para o servidor:
   - `.env` (com suas variáveis de produção)
   - `docker-compose.production.yml` (que está neste repositório)

2. **Login no Docker Registry** (Necessário se o pacote for Private):
   ```bash
   echo "SEU_CR_PAT" | docker login ghcr.io -u SEU_USUARIO_GITHUB --password-stdin
   ```

3. **Subir a aplicação completa**:
   No diretório onde estão os arquivos `.env` e `docker-compose.production.yml`:
   ```bash
   # Baixa as imagens mais recentes
   docker compose -f docker-compose.production.yml pull

   # Sobe todos os serviços (Django + Evolution + Postgres + Redis)
   docker compose -f docker-compose.production.yml up -d
   ```

4. **Acessando os serviços**:
   - **Django App**: `http://IP-DO-SERVIDOR:8000`
   - **Evolution API**: `http://IP-DO-SERVIDOR:8080` (Se a porta estiver liberada no firewall)
   - **PGAdmin**: `http://IP-DO-SERVIDOR:5050`

## 4. Erros Comuns e Troubleshooting

### ❌ Erro: `denied: permission_denied: write_package` na Action
**Causa:** O pacote já existe, mas foi criado por outro repositório ou o `GITHUB_TOKEN` não tem permissão para escrever nele.
**Solução:**
- Se o pacote ainda não existe, verifique se a opção **"Manage Actions permissions"** no repositório está setada como **"Read and write permissions"** em _Settings > Actions > General > Workflow permissions_.
- Se o pacote já existe e foi criado manualmente ou por outro token, vá nas configurações do Pacote (Package Settings) > **Manage Actions access** e adicione o repositório atual com permissão de **Write**.

### ❌ Erro: `pull access denied` no Servidor
**Causa:** Você não está logado no `ghcr.io` ou o pacote é privado e seu token não tem acesso.
**Solução:**
- Gere um novo PAT no GitHub (Settings > Developer settings > tokens (classic)) com escopo `read:packages`.
- Faça login novamente: `docker login ghcr.io`.
- Ou torne o pacote **Public**.

### ❌ Erro: `invalid reference format: repository name must be lowercase`
**Causa:** O nome do seu repositório no GitHub tem letras maiúsculas (ex: `You-Assistente-IA`). O docker exige nomes de imagem em minúsculo.
**Solução:** O workflow que criei já trata isso automaticamente usando a action `docker/metadata-action`, que normaliza o nome da imagem.
- Se estiver rodando `docker pull` manualmente, lembre-se de usar **tudo minúsculo**:
    - ❌ `ghcr.io/Douglas/You-Assistente-IA:latest`
    - ✅ `ghcr.io/douglas/you-assistente-ia:latest`

### ❌ Erro: `invalid reference format` (Trailing Hyphen)
**Causa:** Se o nome do repositório termina com `-` (ex: `You-Assistente-IA-`), isso gera uma tag inválida no Docker.
**Solução:** O workflow foi atualizado para remover automaticamente hifens do final do nome da imagem.

### ❌ Tag `sha` muito longa?
O workflow está configurado para usar `format: short` (7 caracteres), ex: `:a1b2c3d`.
Se precisar do SHA completo, altere no workflow: `format: long`.
