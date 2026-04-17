# 🚀 Copilot Financeiro

> Plataforma web de gestão financeira pessoal inteligente, com IA que organiza receitas e despesas, prevê saldo futuro, detecta padrões de gasto, automatiza lançamentos, interpreta extratos e atua como consultor financeiro.

![stack](https://img.shields.io/badge/stack-Next.js%20%7C%20FastAPI%20%7C%20PostgreSQL-green)
![ai](https://img.shields.io/badge/AI-OpenAI%20GPT-blue)
![ocr](https://img.shields.io/badge/OCR-Tesseract-purple)

---

## ✨ Funcionalidades

### 💳 Gestão Financeira
- Multi-contas (corrente, cartão de crédito, poupança, investimentos, carteira)
- Área **Financeiro** com 4 abas: Recebimentos, Pagamentos, Fluxo de Caixa, Resultados
- Dashboard com KPIs, evolução mensal, gastos por categoria, top categorias em alta
- Categorização hierárquica com categorias de sistema pré-cadastradas
- Parcelamento automático (detecta padrões `3/10`, `parcela X de Y`)

### 📤 Importação Inteligente
- Upload de **OFX, XLSX, PDF** com extração automática de data/descrição/valor
- **OCR com Tesseract** para prints de extratos e faturas
- Deduplicação automática de lançamentos importados
- Histórico completo de importações

### 🧠 IA e Automações
- Motor de categorização baseado em **similaridade textual + aprendizado contínuo**
- Detecção automática de **assinaturas recorrentes** (Netflix, Spotify, academia…)
- Detecção de **parcelamentos** com criação automática das parcelas futuras
- **Previsão de fluxo de caixa** para 90 dias com alertas ("saldo negativo em 40 dias")
- Análise de crescimento de categorias e identificação de desperdícios

### 🤖 Consultor Financeiro IA
- Chat integrado com **OpenAI GPT-4o-mini** que tem acesso completo aos seus dados
- Responde perguntas como:
  - "Onde estou gastando mais?"
  - "Quais assinaturas posso cancelar?"
  - "Quanto gasto por mês com alimentação?"
  - "Qual será meu saldo daqui a 3 meses?"
- Histórico de conversas persistente

### 🛡️ Painel de Administração
- `/admin` protegido por role
- Gestão de usuários (listar, bloquear, redefinir senha, alterar role)
- Visualização de contas, transações, categorias, importações
- **Logs de auditoria** completos de ações administrativas
- Busca global e filtros em todas as tabelas

### 🔐 Segurança
- Login com **e-mail + senha** (bcrypt hashing)
- Login com **Google OAuth 2.0**
- **JWT** com access + refresh token
- Recuperação de senha via e-mail
- **Rate limiting** (5 tentativas/min em login)
- **Lockout automático** após 5 falhas (15 min)
- Verificação de e-mail
- Controle de acesso por `role` (user/admin)

---

## 🏗️ Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| **Frontend** | Next.js 14, React 18, TypeScript, TailwindCSS, Recharts, Zustand, React Query |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Banco** | PostgreSQL 16 + extensões `uuid-ossp`, `pg_trgm` |
| **Cache/Queue** | Redis 7, Celery (worker + beat) |
| **ML** | scikit-learn, similaridade textual (TF-IDF + cosine), embeddings |
| **OCR** | Tesseract (pt-BR) + OpenCV |
| **IA** | OpenAI GPT-4o-mini |
| **Auth** | JWT (jose), bcrypt (passlib), Google OAuth |
| **Infra** | Docker Compose, Vercel (frontend), Railway (backend) |

---

## 📁 Estrutura do Projeto

```
copilot-financeiro/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Endpoints REST (auth, transactions, admin, ai…)
│   │   ├── core/              # config, database, security
│   │   ├── models/            # SQLAlchemy models
│   │   ├── services/          # categorization, import_service
│   │   ├── tasks/             # Celery tasks & scheduler
│   │   ├── main.py            # FastAPI app
│   │   └── seed.py            # Seed inicial (admin + demo)
│   ├── migrations/init.sql    # Schema completo + categorias seed
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/               # App Router (dashboard, financeiro, admin…)
│   │   ├── components/ui/     # Button, Input, Card, Modal…
│   │   ├── components/layout/ # Sidebar, AppShell, Providers
│   │   ├── lib/               # api.ts, utils.ts
│   │   └── store/             # auth.ts (Zustand)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Rodar localmente

### Pré-requisitos
- Docker + Docker Compose
- (Opcional) Node 20+ e Python 3.11+ para rodar fora do Docker

### 1. Clonar e configurar

```bash
git clone https://github.com/seu-usuario/copilot-financeiro.git
cd copilot-financeiro
cp .env.example .env
# Edite .env: OPENAI_API_KEY, GOOGLE_CLIENT_ID/SECRET, SECRET_KEY
```

### 2. Subir com Docker Compose

```bash
docker-compose up -d --build
```

Isso sobe:
- `postgres` na porta 5432
- `redis` na 6379
- `backend` (FastAPI) na 8000
- `celery_worker` + `celery_beat` (jobs async)
- `frontend` (Next.js) na 3000

### 3. Rodar o seed (admin + usuário demo)

```bash
docker exec -it copilot_backend python -m app.seed
```

### 4. Acessar

- 🌐 App: http://localhost:3000
- 📚 API docs: http://localhost:8000/api/docs
- 👤 Login demo: `demo@copilotfinanceiro.com` / `Demo@123`
- 🛡️ Admin: `admin@copilotfinanceiro.com` / `Admin@123`

---

## 🔧 Desenvolvimento local (sem Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Instalar Tesseract (Ubuntu)
sudo apt install tesseract-ocr tesseract-ocr-por

# Subir postgres e redis separadamente
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=copilot_secret postgres:16
docker run -d -p 6379:6379 redis:7

# Rodar
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ☁️ Deploy em Produção

### Opção 1: Vercel (frontend) + Railway (backend + postgres + redis)

#### Backend no Railway

1. Crie um projeto novo no [Railway](https://railway.app/)
2. Adicione os plugins **PostgreSQL** e **Redis**
3. Conecte seu repositório GitHub → pasta `backend`
4. Variáveis de ambiente:
   ```
   DATABASE_URL=<auto do plugin postgres>
   REDIS_URL=<auto do plugin redis>
   SECRET_KEY=<gere com openssl rand -hex 32>
   OPENAI_API_KEY=sk-...
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ALLOWED_ORIGINS=https://seu-app.vercel.app
   ENVIRONMENT=production
   ```
5. Railway usa o `Dockerfile` automaticamente
6. Rode o init SQL: `psql $DATABASE_URL < backend/migrations/init.sql`
7. Rode o seed: `railway run python -m app.seed`

#### Frontend no Vercel

1. Importe o repo no [Vercel](https://vercel.com/)
2. Root directory: `frontend`
3. Framework preset: `Next.js`
4. Variáveis de ambiente:
   ```
   NEXT_PUBLIC_API_URL=https://seu-backend.up.railway.app
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
   ```
5. Deploy automático a cada push

### Opção 2: VPS com Docker Compose

```bash
ssh usuario@seu-servidor
git clone ... && cd copilot-financeiro
cp .env.example .env && nano .env
docker-compose up -d --build
docker exec copilot_backend python -m app.seed

# NGINX reverse proxy (exemplo)
# frontend → localhost:3000
# backend  → localhost:8000
# certbot para SSL
```

---

## 🔑 Configurar Google OAuth

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto → **APIs & Services** → **Credentials**
3. Crie um **OAuth 2.0 Client ID** (Web application)
4. Authorized JavaScript origins: `http://localhost:3000` e sua URL de produção
5. Authorized redirect URIs: não necessário (usamos GSI)
6. Copie `Client ID` e `Client Secret` para o `.env`

---

## 🧠 Como funciona o motor de IA

### Categorização automática (3 camadas)

1. **Correspondência exata** (`category_learning` table): se o usuário já categorizou "UBER TRIP 123" como "Transporte", aplica na próxima
2. **Similaridade textual** (SequenceMatcher, ratio ≥ 0.75): "UBER *TRIP 456" → "Transporte"
3. **Regras por palavra-chave** (fallback): 80+ keywords mapeadas (ifood, netflix, uber, farmácia…)
4. **Sem sugestão**: marca `needs_review=true` para usuário revisar

### Detecção de assinaturas

- Agrupa transações por descrição normalizada
- Verifica consistência de valor (tolerância 10%)
- Analisa intervalos: 30±5 dias = mensal, 7±1 = semanal, 365±5 = anual
- Salva como `suspected` (1ª vez) ou `active` (≥3 ocorrências)

### Previsão de fluxo de caixa

- Média móvel de 6 meses de receitas e despesas
- Adiciona assinaturas ativas e parcelamentos em aberto nas datas esperadas
- Projeta saldo diário por até 365 dias
- Gera alertas: saldo negativo, expense/income ratio > 90%, assinaturas > 15% da renda

### Consultor IA

- Sistema prompt injeta contexto financeiro completo (saldos, gastos do mês, histórico, assinaturas, tendências)
- Cada conversa persistida em `ai_conversations` com JSONB
- Modelo: `gpt-4o-mini` (configurável via `OPENAI_MODEL`)
- Fallback mock quando sem API key (para demo)

---

## 📊 Jobs agendados (Celery Beat)

| Job | Horário | Função |
|-----|---------|--------|
| `detect-subscriptions-daily` | 02:00 | Re-detecta assinaturas para todos os usuários |
| `predict-cashflow-daily` | 03:00 | Atualiza previsões de saldo |
| `weekly-ai-report` | Dom 08:00 | Gera relatório semanal com insights |

---

## 🧪 Testes

```bash
cd backend
pytest tests/ -v
```

---

## 🤝 Contribuindo

1. Fork o projeto
2. `git checkout -b feature/minha-feature`
3. `git commit -m 'feat: adiciona X'`
4. `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📄 Licença

MIT — use, modifique, compartilhe.

---

## 💬 Suporte

- Issues: https://github.com/seu-usuario/copilot-financeiro/issues
- Email: contato@copilotfinanceiro.com

---

**Desenvolvido com 💚 para transformar a vida financeira de quem usa.**
