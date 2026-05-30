# Painel Executivo — Olé Casas × Viana e Moura

Versão web do Painel Olé VM, migrada de um arquivo HTML único para **Next.js + PostgreSQL**, com **login da equipe** e **dados compartilhados** entre todos os usuários, publicada na **Vercel**.

## Como funciona

O painel original (todas as abas, gráficos, KPIs, sprints, kanban e fichas) foi **preservado integralmente** em `public/painel.html` — nenhuma linha do código original foi alterada.

Sobre ele, uma camada fina adiciona:

- **Persistência no banco**: o script `public/ole-bridge.js` substitui o `localStorage` do navegador por uma ponte que lê e grava no PostgreSQL. Assim, o que uma pessoa edita fica salvo para toda a equipe.
- **Login da equipe**: cookie assinado (HMAC). Usuários e senhas ficam na variável `AUTH_USERS`.
- **Migração automática**: na primeira vez que o painel é aberto, se o banco estiver vazio e o navegador tiver dados antigos, eles são enviados para o banco.

## Estrutura

```
public/painel.html        Painel original (intacto)
public/ole-bridge.js      Ponte localStorage -> PostgreSQL
pages/api/painel.js       Serve o painel + injeta o estado do banco
pages/api/state/          GET/POST do estado; import para migração
pages/api/login|logout    Autenticação
pages/login.js            Tela de login
lib/db.js                 Conexão Postgres + tabela kv_state
lib/auth.js               Cookie assinado
middleware.js             Bloqueia acesso sem login
```

## Variáveis de ambiente (configurar na Vercel)

| Variável       | Descrição                                                        |
|----------------|------------------------------------------------------------------|
| `DATABASE_URL` | String de conexão do Postgres (preenchida ao conectar o storage) |
| `AUTH_SECRET`  | String longa e aleatória para assinar o cookie de login          |
| `AUTH_USERS`   | `usuario:senha,usuario2:senha2` — usuários da equipe             |

Veja `.env.example`.

## Rodar localmente

```bash
npm install
cp .env.example .env.local   # edite com seus valores
npm run dev
```

Acesse http://localhost:3000 → será redirecionado ao login.

## Deploy (Vercel)

1. Conectar este repositório do GitHub na Vercel.
2. Em Storage, criar/conectar um **Postgres** (Neon) — isso cria a `DATABASE_URL`.
3. Em Settings → Environment Variables, adicionar `AUTH_SECRET` e `AUTH_USERS`.
4. Deploy. A tabela do banco é criada sozinha no primeiro acesso.
