# Agente de Marketing Instagram — VIVO

Agente que posta automaticamente no Instagram, rodando 100% no GitHub
Actions — não depende do seu computador ligado. Publica dois tipos de
conteúdo, em horários diferentes:

- **Posts estáticos** (imagem única) — todos os dias às **07h30** (horário
  de Brasília).
- **Carrosséis** (2 a 10 imagens) — todos os dias às **18h30** (horário de
  Brasília).

Roteiros de vídeo não são publicados pelo agente — ficam só como conteúdo
de referência salvo no repositório de origem.

## Como funciona

1. Você coloca o conteúdo pendente nas pastas certas (ver `pendentes/posts/LEIA-ME.md`
   e `pendentes/carrosseis/LEIA-ME.md`).
2. Duas vezes por dia, o GitHub Actions roda `script/postar_instagram.py`,
   em um modo diferente conforme o horário:
   - **07h30 → `--modo posts`**: escolhe o próximo post pendente em
     `pendentes/posts/` (ordem alfabética), publica como post único, e move
     o par imagem+legenda para `publicados/posts/`.
   - **18h30 → `--modo carrosseis`**: escolhe a próxima pasta de carrossel
     pendente em `pendentes/carrosseis/` (ordem alfabética), publica todas
     as imagens como carrossel, e move a pasta inteira para
     `publicados/carrosseis/`.
   - Em ambos os casos: publica via Instagram Graph API oficial e commita a
     mudança automaticamente no próprio repositório.
3. Se não houver nada pendente no modo daquele horário, o agente
   simplesmente não faz nada naquela execução (sem erro).
4. Também dá pra rodar manualmente: aba **Actions** → "Postar no Instagram"
   → **Run workflow** → escolher "posts" ou "carrosseis".

## Estrutura

```
agente-instagram-vivo/
├── pendentes/
│   ├── posts/                posts (imagem única) aguardando publicação
│   └── carrosseis/           pastas de carrossel aguardando publicação
├── publicados/
│   ├── posts/                posts já publicados
│   └── carrosseis/           carrosséis já publicados
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

- Adicionar post: solte `nome.jpg` + `nome.txt` em `pendentes/posts/` (ver
  `pendentes/posts/LEIA-ME.md`).
- Adicionar carrossel: crie uma subpasta em `pendentes/carrosseis/` com as
  imagens numeradas + `caption.txt` (ver `pendentes/carrosseis/LEIA-ME.md`).
- Testar manualmente: aba **Actions** do repositório → workflow "Postar no
  Instagram" → **Run workflow** → escolher "posts" ou "carrosseis".
- Ver o que foi publicado: pastas `publicados/posts/` e `publicados/carrosseis/`.
- Ver logs de cada execução: aba **Actions** → clique na execução desejada.

## Avisos importantes

- **Repositório público:** para a API do Meta conseguir "ler" as imagens,
  elas precisam estar em uma URL pública. Isso significa que qualquer
  imagem em `pendentes/` fica acessível via link direto antes de ser
  publicada (não é indexada, mas não é secreta).
- **Token expira a cada 60 dias** — sem renovação, o agente para de postar
  e a execução no Actions aparecerá com erro. Posso configurar um lembrete
  ou automatizar a renovação, se quiser.
- Um post ou um carrossel por execução — no máximo 1 post/dia (07h30) +
  1 carrossel/dia (18h30), ajustável no `postar-instagram.yml`.
- Roteiros de vídeo (`video-scripts/*.md` no content-hub) não são
  publicados por este agente — ficam só como referência salva.
