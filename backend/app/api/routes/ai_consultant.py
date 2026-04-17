from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models import Transaction, Account, Category, AIConversation, SubscriptionDetected

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# =====================================================
# FINANCIAL CONTEXT BUILDER
# =====================================================

async def build_financial_context(user_id: str, db: AsyncSession) -> str:
    """Compila contexto financeiro do usuário para o AI."""
    now = datetime.now()
    month, year = now.month, now.year
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    base = [Transaction.user_id == user_id, Transaction.date >= start, Transaction.date <= end]

    # Current month summary
    income = (await db.execute(
        select(func.sum(Transaction.amount)).where(and_(*base, Transaction.type == "receita"))
    )).scalar() or 0

    expense = (await db.execute(
        select(func.sum(Transaction.amount)).where(and_(*base, Transaction.type == "despesa"))
    )).scalar() or 0

    # By category
    cat_q = (
        select(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(*base, Transaction.type == "despesa"))
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(10)
    )
    cat_result = await db.execute(cat_q)
    by_category = [(r.name, float(r.total)) for r in cat_result.all()]

    # Accounts balance
    acc_result = await db.execute(
        select(Account).where(Account.user_id == user_id, Account.is_active == True)
    )
    accounts = acc_result.scalars().all()

    # Active subscriptions
    sub_result = await db.execute(
        select(SubscriptionDetected).where(
            SubscriptionDetected.user_id == user_id,
            SubscriptionDetected.status == "active",
        )
    )
    subscriptions = sub_result.scalars().all()

    # Last 3 months comparison
    monthly_data = []
    for m in range(max(1, month - 2), month + 1):
        _, ld = monthrange(year, m)
        s = date(year, m, 1)
        e = date(year, m, ld)
        filters = [Transaction.user_id == user_id, Transaction.date >= s, Transaction.date <= e]
        inc = (await db.execute(
            select(func.sum(Transaction.amount)).where(and_(*filters, Transaction.type == "receita"))
        )).scalar() or 0
        exp = (await db.execute(
            select(func.sum(Transaction.amount)).where(and_(*filters, Transaction.type == "despesa"))
        )).scalar() or 0
        monthly_data.append({"month": m, "year": year, "income": float(inc), "expense": float(exp)})

    context = f"""
=== CONTEXTO FINANCEIRO DO USUÁRIO ===
Data atual: {now.strftime('%d/%m/%Y')}

RESUMO DO MÊS ATUAL ({month}/{year}):
- Receitas: R$ {income:,.2f}
- Despesas: R$ {expense:,.2f}
- Saldo do mês: R$ {income - expense:,.2f}

GASTOS POR CATEGORIA ({month}/{year}):
{chr(10).join([f"- {name}: R$ {total:,.2f}" for name, total in by_category])}

CONTAS E SALDOS:
{chr(10).join([f"- {acc.name} ({acc.type}): R$ {acc.balance:,.2f}" for acc in accounts])}

ASSINATURAS ATIVAS:
{chr(10).join([f"- {sub.name}: R$ {sub.amount:,.2f}/mês" for sub in subscriptions]) if subscriptions else "Nenhuma assinatura detectada"}

HISTÓRICO DOS ÚLTIMOS MESES:
{json.dumps(monthly_data, ensure_ascii=False, indent=2)}

Total gasto em assinaturas: R$ {sum(sub.amount for sub in subscriptions):,.2f}/mês
"""
    return context


# =====================================================
# CHAT ENDPOINT
# =====================================================

@router.post("/chat")
async def chat(
    data: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.OPENAI_API_KEY:
        # Mock response for demo
        return {
            "response": _get_mock_response(data.message),
            "conversation_id": data.conversation_id or "demo",
        }

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Load or create conversation
    conversation = None
    if data.conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == data.conversation_id,
                AIConversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            user_id=current_user.id,
            messages=[],
            title=data.message[:60],
        )
        db.add(conversation)
        await db.flush()

    # Build financial context
    financial_context = await build_financial_context(current_user.id, db)

    system_prompt = f"""Você é o Copilot Financeiro, um consultor financeiro pessoal inteligente e empático.

Você tem acesso completo aos dados financeiros do usuário e deve responder perguntas sobre finanças pessoais de forma clara, prática e personalizada.

{financial_context}

DIRETRIZES:
- Sempre use os dados reais do usuário nas respostas
- Seja específico com valores em R$
- Dê recomendações práticas e acionáveis
- Use linguagem acessível, sem jargões desnecessários
- Se o usuário perguntar sobre o futuro, use os padrões históricos para prever
- Detecte oportunidades de economia baseado nos dados
- Seja encorajador mas honesto sobre gastos excessivos
- Responda em português brasileiro
"""

    messages = list(conversation.messages or [])
    messages.append({"role": "user", "content": data.message})

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            max_tokens=1000,
            temperature=0.7,
        )
        assistant_message = response.choices[0].message.content

        messages.append({"role": "assistant", "content": assistant_message})
        conversation.messages = messages

        return {
            "response": assistant_message,
            "conversation_id": conversation.id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao comunicar com IA: {str(e)}")


@router.get("/conversations")
async def list_conversations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(20)
    )
    conversations = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "message_count": len(c.messages or []),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return {"id": conv.id, "title": conv.title, "messages": conv.messages}


def _get_mock_response(message: str) -> str:
    """Mock response when OpenAI is not configured."""
    lower = message.lower()
    if "gasto" in lower or "gastando" in lower:
        return "📊 Analisando seus dados, seus maiores gastos este mês são: Alimentação (R$ 1.200), Transporte (R$ 450) e Assinaturas (R$ 280). Você está gastando 15% mais em alimentação comparado ao mês passado."
    elif "saldo" in lower or "quanto tenho" in lower:
        return "💰 Seu saldo atual consolidado é de R$ 4.850,00. Considerando seus padrões de gasto, a previsão é que você termine o mês com aproximadamente R$ 2.100,00."
    elif "assinatura" in lower:
        return "🔄 Você tem 6 assinaturas ativas totalizando R$ 280/mês: Netflix (R$ 45), Spotify (R$ 21), Amazon Prime (R$ 14), Disney+ (R$ 38), Academia (R$ 120) e Jornal Digital (R$ 42). Você já considerou revisar as que usa menos?"
    elif "economizar" in lower or "economia" in lower:
        return "💡 Identifiquei 3 oportunidades de economia: (1) Restaurantes: R$ 680/mês - cozinhar mais em casa pode economizar R$ 300; (2) Assinaturas: cancelar as 2 menos usadas pode economizar R$ 60/mês; (3) Combustível: usar transporte público 2x/semana pode economizar R$ 150/mês. Total potencial: R$ 510/mês!"
    elif "previsão" in lower or "futuro" in lower or "meses" in lower:
        return "🔮 Com base nos seus padrões atuais, em 3 meses: Receitas previstas: R$ 18.000 | Despesas previstas: R$ 14.400 | Saldo acumulado previsto: R$ 3.600. Atenção: se mantiver o crescimento de gastos em restaurantes (+23%/mês), o saldo pode ser R$ 800 menor."
    else:
        return "Olá! Sou o seu Copilot Financeiro 🤖. Posso ajudar você a entender seus gastos, identificar economias, detectar padrões e fazer previsões financeiras. O que gostaria de saber? Configure a chave OpenAI para respostas personalizadas com seus dados reais."
