# Agente de Marketing Instagram — VIVO

Agente que posta automaticamente no Instagram, 2x por dia (07h30 e 18h30,
horário de Brasília), rodando 100% no GitHub Actions — não depende do seu
computador ligado.

## Como funciona

1. Você coloca pares de arquivos (`imagem.jpg` + `imagem.txt` com a legenda)
   na pasta `pendentes/`.
2. Duas vezes por dia, o GitHub Actions roda `script/postar_instagram.py`,
   que:
   - escolhe o próximo post pendente (ordem alfabética do nome do arquivo);
   - publica no Instagram usando a API oficial da Meta (Graph API);
   - move o par publicado de `pendentes/` para `publicados/` e salva isso
     como um commit no próprio repositório.
3. Se `pendentes/` estiver vazia, o agente simplesmente não faz nada
   naquela execução (sem erro).

## Estrutura

```
agente-instagram-vivo/
├── pendentes/              posts aguardando publicação
├── publicados/             posts já publicados (organizado automaticamente)
├── script/
│   ├── postar_instagram.py
│   └── requirements.txt
└── .github/workflows/
    └── postar-instagram.yml   agendamento (cron) + execução
```

---

## Configuração única (antes do agente funcionar)

Você já tem parte disso configurado — revise cada item abaixo.

### 1. Conta do Instagram como Business ou Creator
No app do Instagram: Configurações → Conta → Alternar para conta profissional
→ Business (ou Creator).

### 2. Vincular a uma Página do Facebook
A conta profissional do Instagram precisa estar conectada a uma Página do
Facebook (não ao seu perfil pessoal). Isso se faz em: Configurações da
Página do Facebook → Contas vinculadas → Instagram.

### 3. Criar um App no Meta for Developers
1. Acesse https://developers.facebook.com/apps e clique em **Criar app**.
2. Tipo de app: **Business**.
3. No painel do app, adicione o produto **Instagram Graph API** (ou
   "Instagram API with Facebook Login for Business", dependendo da versão
   do painel).

### 4. Gerar um token de acesso de longa duração
1. No app criado, vá em **Ferramentas → Graph API Explorer**.
2. Selecione o app, e nas permissões marque: `instagram_basic`,
   `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`,
   `business_management`.
3. Gere um **token de usuário** (short-lived).
4. Troque esse token por um de **longa duração** (60 dias) usando o endpoint:
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
       ?grant_type=fb_exchange_token
       &client_id={APP_ID}
       &client_secret={APP_SECRET}
       &fb_exchange_token={TOKEN_CURTO}
   ```
   (APP_ID e APP_SECRET ficam em Configurações básicas do app.)

   ⚠️ **Este token expira em ~60 dias.** Anote uma data para renovar (ou me
   avise para automatizarmos a renovação depois).

### 5. Descobrir os IDs necessários
1. ID da Página do Facebook:
   `GET https://graph.facebook.com/v21.0/me/accounts?access_token={TOKEN}`
2. ID da conta Business do Instagram (o que o agente precisa):
   ```
   GET https://graph.facebook.com/v21.0/{PAGE_ID}
       ?fields=instagram_business_account
       &access_token={TOKEN}
   ```
   O valor retornado em `instagram_business_account.id` é o
   `IG_BUSINESS_ACCOUNT_ID`.

### 6. Cadastrar os Secrets no GitHub
No repositório: **Settings → Secrets and variables → Actions → New
repository secret**, criar:

| Nome | Valor |
|---|---|
| `IG_ACCESS_TOKEN` | o token de longa duração do passo 4 |
| `IG_BUSINESS_ACCOUNT_ID` | o ID do passo 5 |

Não é preciso configurar nada de Git/GitHub token — o próprio
`GITHUB_TOKEN` do Actions cuida do commit automático (permissão já
habilitada no workflow).

---

## Uso do dia a dia

- Adicionar posts: solte `nome.jpg` + `nome.txt` em `pendentes/` (ver
  `pendentes/LEIA-ME.md`).
- Testar manualmente: aba **Actions** do repositório → workflow "Postar no
  Instagram" → **Run workflow**.
- Ver o que foi publicado: pasta `publicados/`.
- Ver logs de cada execução: aba **Actions** → clique na execução desejada.

## Avisos importantes

- **Repositório público:** para a API do Meta conseguir "ler" a imagem, ela
  precisa estar em uma URL pública. Isso significa que qualquer imagem em
  `pendentes/` fica acessível via link direto antes de ser publicada (não é
  indexada, mas não é secreta).
- **Token expira a cada 60 dias** — sem renovação, o agente para de postar
  e a execução no Actions aparecerá com erro. Posso configurar um lembrete
  ou automatizar a renovação, se quiser.
- Um post por execução — com 2 horários por dia, é 2 posts/dia no máximo
  (ajustável no `postar-instagram.yml`).
