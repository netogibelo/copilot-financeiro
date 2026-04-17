# 🚢 Guia de Deploy - Copilot Financeiro

Este guia cobre 3 cenários de deploy:
1. **Local (desenvolvimento)** — Docker Compose
2. **Produção cloud** — Vercel + Railway (recomendado)
3. **VPS self-hosted** — Docker + NGINX

---

## 1️⃣ Deploy Local (Docker Compose)

### Pré-requisitos
- Docker 24+
- Docker Compose v2

### Passos

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/copilot-financeiro.git
cd copilot-financeiro

# Copiar variáveis de ambiente
cp .env.example .env

# Editar .env e preencher:
# - SECRET_KEY (gere com: openssl rand -hex 32)
# - OPENAI_API_KEY (opcional, mas recomendado)
# - GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET (para login Google)
nano .env

# Subir tudo
docker-compose up -d --build

# Rodar seed inicial
docker exec -it copilot_backend python -m app.seed

# Verificar logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Acessar
- App: http://localhost:3000
- API docs: http://localhost:8000/api/docs
- Login demo: `demo@copilotfinanceiro.com` / `Demo@123`
- Admin: `admin@copilotfinanceiro.com` / `Admin@123`

### Parar
```bash
docker-compose down          # mantém volumes
docker-compose down -v       # remove volumes (perde dados)
```

---

## 2️⃣ Deploy em Produção (Vercel + Railway)

Arquitetura recomendada para SaaS: frontend na Vercel (edge network global) e backend + bancos no Railway.

### 2.1. Backend no Railway

#### A. Criar projeto

1. Acesse https://railway.app/ → **New Project** → **Deploy from GitHub**
2. Selecione o repositório `copilot-financeiro`
3. Em **Service Settings** → **Root Directory**: `backend`
4. **Builder**: Dockerfile (detectado automaticamente)

#### B. Adicionar PostgreSQL

1. No painel do projeto → **New** → **Database** → **PostgreSQL**
2. Railway cria um plugin e gera automaticamente `DATABASE_URL`

#### C. Adicionar Redis

1. **New** → **Database** → **Redis**
2. Railway gera `REDIS_URL`

#### D. Variáveis de ambiente do backend

No serviço backend → **Variables**:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<openssl rand -hex 32>
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
GOOGLE_CLIENT_ID=seu-client-id
GOOGLE_CLIENT_SECRET=seu-secret
ALLOWED_ORIGINS=https://seu-app.vercel.app
ENVIRONMENT=production
ADMIN_EMAIL=admin@seudominio.com
ADMIN_PASSWORD=<senha-forte>
PORT=8000
```

#### E. Aplicar migrations

Railway oferece um **Deploy Logs** com um terminal. Ou use CLI:

```bash
# Instalar Railway CLI
npm i -g @railway/cli
railway login
railway link  # conecta ao seu projeto

# Rodar migrations
railway run psql $DATABASE_URL < backend/migrations/init.sql

# Rodar seed
railway run python -m app.seed
```

#### F. Configurar workers Celery (opcional)

Crie 2 serviços adicionais (mesmo repositório, pasta `backend`):
- **copilot_celery_worker**: start command → `celery -A app.tasks.celery_app worker --loglevel=info`
- **copilot_celery_beat**: start command → `celery -A app.tasks.celery_app beat --loglevel=info`

Ambos usam as mesmas variáveis de ambiente do backend.

#### G. Gerar domínio público

Railway → **Settings** → **Generate Domain** → `https://copilot-backend.up.railway.app`

Teste: `curl https://copilot-backend.up.railway.app/health`

---

### 2.2. Frontend na Vercel

#### A. Importar projeto

1. https://vercel.com/new → **Import Git Repository** → selecione `copilot-financeiro`
2. **Root Directory**: `frontend`
3. **Framework Preset**: Next.js (auto-detectado)
4. **Build Command**: `npm run build` (default)

#### B. Variáveis de ambiente

```env
NEXT_PUBLIC_API_URL=https://copilot-backend.up.railway.app
NEXT_PUBLIC_GOOGLE_CLIENT_ID=seu-google-client-id
```

#### C. Deploy

Clique em **Deploy**. Vercel faz o build e publica em `https://seu-app.vercel.app`.

#### D. Domínio customizado (opcional)

**Settings** → **Domains** → **Add** `app.seudominio.com`
- Configure o DNS do seu domínio apontando para `cname.vercel-dns.com`

---

### 2.3. Google OAuth - configurar domínios

Após ter as URLs de produção, volte ao Google Cloud Console:

1. **Credentials** → edite seu OAuth 2.0 Client ID
2. **Authorized JavaScript origins**:
   - `http://localhost:3000`
   - `https://seu-app.vercel.app`
   - `https://app.seudominio.com` (se tiver domínio próprio)

Salve. O Google leva alguns minutos para propagar.

---

### 2.4. Configurar CORS no backend

Garanta que `ALLOWED_ORIGINS` no Railway contenha exatamente a URL do frontend:

```env
ALLOWED_ORIGINS=https://seu-app.vercel.app,https://app.seudominio.com
```

Redeploy o backend após essa mudança.

---

## 3️⃣ Deploy VPS (Docker + NGINX + Let's Encrypt)

### Pré-requisitos
- VPS Ubuntu 22.04+ (mínimo 2 vCPU, 4 GB RAM)
- Domínio com DNS apontando para o IP do servidor
- Docker + Docker Compose instalados

### 3.1. Setup inicial

```bash
ssh usuario@seu-servidor.com

# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Instalar NGINX e certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Clonar projeto
git clone https://github.com/seu-usuario/copilot-financeiro.git
cd copilot-financeiro
cp .env.example .env
nano .env  # preencher tudo
```

### 3.2. Subir stack

```bash
docker-compose up -d --build
docker exec copilot_backend python -m app.seed
```

### 3.3. NGINX reverse proxy

Crie `/etc/nginx/sites-available/copilot`:

```nginx
# Frontend
server {
    listen 80;
    server_name app.seudominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    listen 80;
    server_name api.seudominio.com;

    client_max_body_size 50M;  # para uploads de arquivos

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/copilot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.4. SSL com Let's Encrypt

```bash
sudo certbot --nginx -d app.seudominio.com -d api.seudominio.com
```

Certbot configura HTTPS automaticamente e renova os certificados.

### 3.5. Atualizar variáveis e reiniciar

```bash
nano .env
# Atualize:
# NEXT_PUBLIC_API_URL=https://api.seudominio.com
# ALLOWED_ORIGINS=https://app.seudominio.com

docker-compose down
docker-compose up -d --build
```

---

## 🔐 Checklist de Segurança (Produção)

- [ ] `SECRET_KEY` forte e único (32+ chars aleatórios)
- [ ] Senha do admin padrão trocada após primeiro login
- [ ] HTTPS habilitado (Let's Encrypt ou Cloudflare)
- [ ] `ENVIRONMENT=production` no backend (desabilita SQL echo)
- [ ] PostgreSQL com senha forte e não exposta publicamente
- [ ] Redis com `requirepass` se exposto
- [ ] Rate limiting habilitado (já está em `/auth/login` e `/auth/forgot-password`)
- [ ] Backup automático do Postgres (use `pg_dump` agendado via cron)
- [ ] Monitoramento (ex.: Sentry, Datadog, UptimeRobot)
- [ ] CORS restrito a domínios específicos
- [ ] Google OAuth configurado com origins corretos

---

## 📦 Backup do banco de dados

```bash
# Dump
docker exec copilot_db pg_dump -U copilot copilot_financeiro > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i copilot_db psql -U copilot copilot_financeiro < backup_20251017.sql
```

### Backup automatizado (cron)

```bash
# /etc/cron.daily/copilot-backup
#!/bin/bash
DIR=/var/backups/copilot
mkdir -p $DIR
docker exec copilot_db pg_dump -U copilot copilot_financeiro | gzip > $DIR/copilot_$(date +\%Y\%m\%d).sql.gz
find $DIR -name "copilot_*.sql.gz" -mtime +30 -delete  # mantém 30 dias
```

---

## 🔄 Atualizar para nova versão

```bash
cd copilot-financeiro
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Se houver migrations novas:
docker exec copilot_backend python -m app.seed  # idempotente
```

---

## 📈 Escalabilidade

Para cargas maiores:

- **Backend**: aumente `pool_size` e `max_overflow` em `database.py`. Use gunicorn com múltiplos workers: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
- **Celery**: múltiplos workers com concurrency: `celery ... worker -c 8`
- **PostgreSQL**: replicação read-only, pooling com PgBouncer
- **Redis**: Redis Cluster para alta disponibilidade
- **CDN**: Vercel já entrega frontend via edge network global

---

## 🆘 Troubleshooting

### Erro "connection refused" ao postgres
```bash
docker-compose logs postgres
# verifique se healthcheck passou
docker exec copilot_db pg_isready
```

### Tesseract não encontra idioma português
```bash
docker exec copilot_backend apt list --installed | grep tesseract
# Se faltar: docker exec copilot_backend apt install tesseract-ocr-por
```

### OpenAI retorna erro 429
- Aumente sua cota na OpenAI
- Temporariamente comente `OPENAI_API_KEY` no `.env` — o sistema usa fallback mock

### Frontend não conecta ao backend
- Verifique `NEXT_PUBLIC_API_URL` no Vercel
- Confira `ALLOWED_ORIGINS` no backend
- Abra DevTools → Network, veja o erro específico

---

**Pronto! Seu Copilot Financeiro está no ar. 🚀**
