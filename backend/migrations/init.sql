-- =====================================================
-- COPILOT FINANCEIRO - Database Schema
-- PostgreSQL 16
-- =====================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- ENUMS
-- =====================================================

CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE account_type AS ENUM ('corrente', 'poupanca', 'cartao_credito', 'investimento', 'carteira', 'outro');
CREATE TYPE transaction_type AS ENUM ('receita', 'despesa', 'transferencia', 'investimento');
CREATE TYPE category_type AS ENUM ('receita', 'despesa', 'investimento', 'transferencia');
CREATE TYPE import_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'suspected');

-- =====================================================
-- USERS
-- =====================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    role user_role NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_role ON users(role);

-- =====================================================
-- ACCOUNTS
-- =====================================================

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type account_type NOT NULL,
    bank_name VARCHAR(255),
    balance DECIMAL(15,2) NOT NULL DEFAULT 0,
    credit_limit DECIMAL(15,2),
    closing_day INTEGER,
    due_day INTEGER,
    color VARCHAR(7) DEFAULT '#6366f1',
    icon VARCHAR(50) DEFAULT 'wallet',
    is_active BOOLEAN NOT NULL DEFAULT true,
    include_in_total BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_accounts_user_id ON accounts(user_id);

-- =====================================================
-- CATEGORIES
-- =====================================================

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type category_type NOT NULL,
    icon VARCHAR(50) DEFAULT 'tag',
    color VARCHAR(7) DEFAULT '#6366f1',
    parent_id UUID REFERENCES categories(id),
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name, type)
);

CREATE INDEX idx_categories_user_id ON categories(user_id);
CREATE INDEX idx_categories_type ON categories(type);

-- =====================================================
-- TRANSACTIONS
-- =====================================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id),
    type transaction_type NOT NULL,
    description VARCHAR(500) NOT NULL,
    original_description VARCHAR(500),
    amount DECIMAL(15,2) NOT NULL,
    date DATE NOT NULL,
    is_paid BOOLEAN NOT NULL DEFAULT true,
    notes TEXT,
    tags VARCHAR(255)[],
    -- Parcelamento
    installment_total INTEGER,
    installment_current INTEGER,
    installment_group_id UUID,
    -- Transferência
    transfer_account_id UUID REFERENCES accounts(id),
    -- Metadados
    import_id UUID,
    is_recurring BOOLEAN DEFAULT false,
    recurring_group_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_category_id ON transactions(category_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_installment_group ON transactions(installment_group_id);
CREATE INDEX idx_transactions_description_trgm ON transactions USING GIN(description gin_trgm_ops);

-- =====================================================
-- CATEGORY LEARNING (ML)
-- =====================================================

CREATE TABLE category_learning (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern VARCHAR(500) NOT NULL,
    category_id UUID NOT NULL REFERENCES categories(id),
    confidence DECIMAL(5,4) DEFAULT 1.0,
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, pattern)
);

CREATE INDEX idx_category_learning_user_id ON category_learning(user_id);
CREATE INDEX idx_category_learning_pattern_trgm ON category_learning USING GIN(pattern gin_trgm_ops);

-- =====================================================
-- SUBSCRIPTIONS DETECTED
-- =====================================================

CREATE TABLE subscriptions_detected (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    category_id UUID REFERENCES categories(id),
    account_id UUID REFERENCES accounts(id),
    frequency_days INTEGER NOT NULL DEFAULT 30,
    last_detected_at DATE,
    next_expected_at DATE,
    status subscription_status DEFAULT 'suspected',
    pattern_keyword VARCHAR(255),
    transaction_ids UUID[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions_detected(user_id);

-- =====================================================
-- INSTALLMENTS DETECTED
-- =====================================================

CREATE TABLE installments_detected (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    installment_amount DECIMAL(15,2) NOT NULL,
    total_installments INTEGER NOT NULL,
    paid_installments INTEGER NOT NULL DEFAULT 0,
    remaining_installments INTEGER NOT NULL,
    start_date DATE,
    end_date DATE,
    category_id UUID REFERENCES categories(id),
    account_id UUID REFERENCES accounts(id),
    group_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_installments_user_id ON installments_detected(user_id);

-- =====================================================
-- CASHFLOW PREDICTIONS
-- =====================================================

CREATE TABLE cashflow_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prediction_date DATE NOT NULL,
    predicted_balance DECIMAL(15,2),
    predicted_income DECIMAL(15,2),
    predicted_expense DECIMAL(15,2),
    confidence_score DECIMAL(5,4),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(50),
    UNIQUE(user_id, prediction_date)
);

CREATE INDEX idx_cashflow_user_id ON cashflow_predictions(user_id);
CREATE INDEX idx_cashflow_date ON cashflow_predictions(prediction_date);

-- =====================================================
-- IMPORTS
-- =====================================================

CREATE TABLE imports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id),
    filename VARCHAR(500),
    file_type VARCHAR(20),
    status import_status DEFAULT 'pending',
    total_transactions INTEGER DEFAULT 0,
    imported_transactions INTEGER DEFAULT 0,
    duplicate_transactions INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_imports_user_id ON imports(user_id);

-- =====================================================
-- AI CHAT HISTORY
-- =====================================================

CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    messages JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_conversations_user_id ON ai_conversations(user_id);

-- =====================================================
-- AUDIT LOGS
-- =====================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    admin_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- =====================================================
-- USAGE ANALYTICS
-- =====================================================

CREATE TABLE usage_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    page VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analytics_user_id ON usage_analytics(user_id);
CREATE INDEX idx_analytics_event_type ON usage_analytics(event_type);
CREATE INDEX idx_analytics_created_at ON usage_analytics(created_at);

-- =====================================================
-- SYSTEM CATEGORIES (seed)
-- =====================================================

INSERT INTO categories (id, user_id, name, type, icon, color, is_system) VALUES
-- Receitas
(uuid_generate_v4(), NULL, 'Salário', 'receita', 'briefcase', '#22c55e', true),
(uuid_generate_v4(), NULL, 'Freelance', 'receita', 'laptop', '#16a34a', true),
(uuid_generate_v4(), NULL, 'Investimentos', 'receita', 'trending-up', '#15803d', true),
(uuid_generate_v4(), NULL, 'Aluguel Recebido', 'receita', 'home', '#166534', true),
(uuid_generate_v4(), NULL, 'Outros Recebimentos', 'receita', 'plus-circle', '#14532d', true),
-- Despesas
(uuid_generate_v4(), NULL, 'Alimentação', 'despesa', 'utensils', '#ef4444', true),
(uuid_generate_v4(), NULL, 'Transporte', 'despesa', 'car', '#dc2626', true),
(uuid_generate_v4(), NULL, 'Moradia', 'despesa', 'home', '#b91c1c', true),
(uuid_generate_v4(), NULL, 'Saúde', 'despesa', 'heart', '#991b1b', true),
(uuid_generate_v4(), NULL, 'Educação', 'despesa', 'book', '#7f1d1d', true),
(uuid_generate_v4(), NULL, 'Lazer', 'despesa', 'smile', '#f97316', true),
(uuid_generate_v4(), NULL, 'Assinaturas', 'despesa', 'repeat', '#ea580c', true),
(uuid_generate_v4(), NULL, 'Vestuário', 'despesa', 'shopping-bag', '#c2410c', true),
(uuid_generate_v4(), NULL, 'Beleza', 'despesa', 'scissors', '#9a3412', true),
(uuid_generate_v4(), NULL, 'Pets', 'despesa', 'paw-print', '#7c2d12', true),
(uuid_generate_v4(), NULL, 'Supermercado', 'despesa', 'shopping-cart', '#fbbf24', true),
(uuid_generate_v4(), NULL, 'Restaurante', 'despesa', 'coffee', '#f59e0b', true),
(uuid_generate_v4(), NULL, 'Farmácia', 'despesa', 'plus', '#d97706', true),
(uuid_generate_v4(), NULL, 'Combustível', 'despesa', 'droplets', '#b45309', true),
(uuid_generate_v4(), NULL, 'Streaming', 'despesa', 'play', '#92400e', true),
(uuid_generate_v4(), NULL, 'Academia', 'despesa', 'dumbbell', '#78350f', true),
(uuid_generate_v4(), NULL, 'Viagens', 'despesa', 'plane', '#8b5cf6', true),
(uuid_generate_v4(), NULL, 'Eletrônicos', 'despesa', 'smartphone', '#7c3aed', true),
(uuid_generate_v4(), NULL, 'Outros Gastos', 'despesa', 'more-horizontal', '#6d28d9', true),
-- Investimentos
(uuid_generate_v4(), NULL, 'Renda Fixa', 'investimento', 'shield', '#3b82f6', true),
(uuid_generate_v4(), NULL, 'Renda Variável', 'investimento', 'bar-chart', '#2563eb', true),
(uuid_generate_v4(), NULL, 'Criptomoedas', 'investimento', 'bitcoin', '#1d4ed8', true),
(uuid_generate_v4(), NULL, 'Fundos', 'investimento', 'package', '#1e40af', true),
-- Transferência
(uuid_generate_v4(), NULL, 'Transferência entre Contas', 'transferencia', 'arrow-right', '#6b7280', true);

-- =====================================================
-- UPDATED_AT TRIGGER
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_accounts_updated_at BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_categories_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_transactions_updated_at BEFORE UPDATE ON transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_category_learning_updated_at BEFORE UPDATE ON category_learning FOR EACH ROW EXECUTE FUNCTION update_updated_at();
