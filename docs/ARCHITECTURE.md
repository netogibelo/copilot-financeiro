# 🏛️ Arquitetura - Copilot Financeiro

## Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                      NAVEGADOR                          │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 14)                  │
│  • App Router • Server Components                       │
│  • Zustand (auth)  • React Query (cache)                │
│  • TailwindCSS  • Recharts                              │
│  • Vercel Edge Network                                  │
└───────────────────────────┬─────────────────────────────┘
                            │ REST /api/v1
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI + Python)              │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Middlewares: CORS, Rate Limit, JWT              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Routes (13 routers)                             │   │
│  │  /auth  /users  /accounts  /categories          │   │
│  │  /transactions  /imports  /subscriptions        │   │
│  │  /cashflow  /ai  /admin  /analytics  /reports   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Services                                        │   │
│  │  • CategorizationService (ML)                   │   │
│  │  • ImportService (OFX/XLSX/PDF/OCR)             │   │
│  │  • AI Consultant (OpenAI)                       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Models (SQLAlchemy async)                       │   │
│  └──────────────────────────────────────────────────┘   │
└──────┬──────────────────────┬───────────────────┬───────┘
       │                      │                   │
       ▼                      ▼                   ▼
┌──────────────┐     ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │     │    Redis     │    │  OpenAI API  │
│  • 11 tables │     │  • Broker    │    │  • GPT-4o    │
│  • pg_trgm   │     │  • Cache     │    │  • Contexto  │
│  • uuid-ossp │     │              │    │    do user   │
└──────────────┘     └──────┬───────┘    └──────────────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │  Celery Workers   │
                    │  • Worker         │
                    │  • Beat (cron)    │
                    │  • Tesseract OCR  │
                    └───────────────────┘
```

## Fluxo de dados principais

### 1. Importação de extrato

```
Usuário → Upload (OFX/XLSX/PDF/Imagem)
  → Backend recebe multipart
  → ImportService.parse_file()
      ├─ OFX → ofxparse
      ├─ XLSX → pandas
      ├─ PDF → PyMuPDF extrai texto → regex
      └─ Imagem → OpenCV preprocess → Tesseract OCR → regex
  → Para cada transação:
      ├─ Deduplicação (data + valor + descrição)
      ├─ CategorizationService.suggest_category()
      │     1. Match exato em category_learning
      │     2. Fuzzy match (SequenceMatcher ≥ 0.75)
      │     3. Keyword rules (80+ mapeamentos)
      │     4. needs_review=true
      └─ detect_installments (regex 3/10, parcela X de Y)
  → Salva em transactions
  → Retorna preview ao frontend
```

### 2. Consultor IA

```
Usuário → pergunta no chat
  → Backend constrói contexto:
      ├─ Resumo do mês atual (receitas, despesas, saldo)
      ├─ Top 10 categorias do mês
      ├─ Saldos de todas as contas
      ├─ Assinaturas ativas
      └─ Histórico 3 meses
  → Monta system prompt com dados reais
  → Chama OpenAI API (gpt-4o-mini)
  → Salva conversa em ai_conversations (JSONB)
  → Retorna resposta ao usuário
```

### 3. Detecção de assinaturas (background)

```
Celery Beat (diário 02:00)
  → Para cada usuário ativo:
      → Busca transações dos últimos 180 dias
      → Agrupa por descrição normalizada
      → Para cada grupo com ≥ 2 ocorrências:
          ├─ Verifica consistência de valor (tolerância 10%)
          ├─ Calcula intervalos entre datas
          ├─ Classifica frequência:
          │     • 7±1 dias → semanal
          │     • 30±5 dias → mensal
          │     • 365±5 dias → anual
          └─ Salva/atualiza em subscriptions_detected
              status = 'active' (≥3) ou 'suspected' (2)
```

### 4. Previsão de fluxo de caixa

```
GET /cashflow/predict?days=90
  → Calcula média móvel 6 meses (receitas + despesas)
  → Busca saldo atual consolidado (accounts)
  → Busca assinaturas ativas e datas previstas
  → Busca parcelamentos em aberto
  → Para cada dia projetado:
      saldo += receita_media_diaria
      saldo -= despesa_media_diaria
      saldo -= assinaturas_daquele_dia
      saldo -= fracao_parcela_mensal
  → Gera alertas:
      • Saldo negativo em X dias
      • Expense/income > 90%
      • Assinaturas > 15% da renda
  → Salva em cashflow_predictions (semanalmente)
```

## Segurança por camada

### Frontend
- Tokens em localStorage com auto-refresh
- Interceptor axios invalida sessão em 401
- Rotas privadas via AppShell (verifica auth + redirect)
- Role check para `/admin`

### Backend
- **Senhas**: bcrypt (12 rounds)
- **JWT**: HS256, access 24h + refresh 30d
- **Rate limiting**: 5/min em endpoints de auth
- **Lockout**: 5 falhas → 15 min bloqueado
- **CORS**: whitelist de origins
- **SQL Injection**: SQLAlchemy parametrizado
- **File upload**: validação de MIME + tamanho
- **Admin actions**: logged em `audit_logs`

### Database
- Foreign keys com `ON DELETE CASCADE`
- Indexes em campos de busca frequente
- Extensão `pg_trgm` para busca fuzzy
- Triggers `updated_at` automáticos

## Estratégias de aprendizado contínuo

1. **category_learning**: cada correção manual do usuário incrementa `usage_count` e ajusta a associação pattern → category
2. **usage_analytics** (futuro): tracking de páginas acessadas e ações para otimização de UX
3. **audit_logs**: histórico completo para debugar e auditar
4. **weekly_reports** (Celery): gera insights automáticos baseados em uso real

## Escolhas técnicas

| Decisão | Razão |
|---------|-------|
| **FastAPI async** | Performance + docs automáticas + type hints |
| **SQLAlchemy 2.0 async** | Concorrência em queries I/O-bound |
| **Zustand** | API mais simples que Redux, sem boilerplate |
| **React Query** | Cache inteligente, invalidação declarativa |
| **Celery** | Jobs longos (OCR, ML) não bloqueiam request |
| **PostgreSQL** | ACID + JSONB + extensões (pg_trgm) |
| **Tesseract local** | Sem custo por request (ao contrário de APIs) |
| **OpenAI gpt-4o-mini** | Qualidade alta com custo muito baixo (~$0.15/1M tokens) |
| **Next.js App Router** | Server components + streaming + SEO |
| **Docker Compose** | Reprodutibilidade entre dev/prod |
