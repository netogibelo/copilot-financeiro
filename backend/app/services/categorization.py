"""
Motor de categorização automática baseado em:
1. Correspondência exata de padrão aprendido
2. Similaridade textual (TF-IDF + cosine)
3. Regras de negócio (palavras-chave)
4. Fallback: perguntar ao usuário
"""

import re
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import CategoryLearning, Category


# =====================================================
# KEYWORD RULES (fallback)
# =====================================================

KEYWORD_RULES = {
    # Alimentação
    "ifood": "Alimentação", "rappi": "Alimentação", "uber eat": "Alimentação",
    "restaurante": "Restaurante", "lanche": "Alimentação", "pizza": "Alimentação",
    "burger": "Alimentação", "mcdonalds": "Restaurante", "subway": "Restaurante",
    "starbucks": "Restaurante", "padaria": "Alimentação",

    # Supermercado
    "mercado": "Supermercado", "carrefour": "Supermercado", "extra": "Supermercado",
    "atacadao": "Supermercado", "assai": "Supermercado", "sams club": "Supermercado",
    "pao de acucar": "Supermercado", "dia": "Supermercado", "hortifruti": "Supermercado",

    # Transporte
    "uber": "Transporte", "99": "Transporte", "cabify": "Transporte",
    "metro": "Transporte", "onibus": "Transporte", "passagem": "Transporte",
    "estacionamento": "Transporte", "pedagio": "Transporte",

    # Combustível
    "posto": "Combustível", "petrobras": "Combustível", "shell": "Combustível",
    "ipiranga": "Combustível", "br distribuidora": "Combustível",
    "gasolina": "Combustível", "etanol": "Combustível",

    # Streaming
    "netflix": "Streaming", "spotify": "Streaming", "disney": "Streaming",
    "amazon prime": "Streaming", "hbo": "Streaming", "apple tv": "Streaming",
    "youtube premium": "Streaming", "deezer": "Streaming", "globoplay": "Streaming",
    "paramount": "Streaming", "crunchyroll": "Streaming",

    # Academia
    "academia": "Academia", "smart fit": "Academia", "bluefit": "Academia",
    "bodytech": "Academia", "crossfit": "Academia", "fitness": "Academia",

    # Saúde
    "farmacia": "Farmácia", "droga": "Farmácia", "ultrafarma": "Farmácia",
    "drogaria": "Farmácia", "medico": "Saúde", "consulta": "Saúde",
    "hospital": "Saúde", "laboratorio": "Saúde", "plano de saude": "Saúde",
    "unimed": "Saúde", "amil": "Saúde",

    # Educação
    "escola": "Educação", "faculdade": "Educação", "universidade": "Educação",
    "curso": "Educação", "udemy": "Educação", "alura": "Educação",
    "mensalidade": "Educação",

    # Moradia
    "aluguel": "Moradia", "condominio": "Moradia", "agua": "Moradia",
    "luz": "Moradia", "energia": "Moradia", "gas": "Moradia",
    "internet": "Moradia", "vivo": "Moradia", "claro": "Moradia",
    "tim": "Moradia", "oi ": "Moradia",

    # Vestuário
    "zara": "Vestuário", "renner": "Vestuário", "c&a": "Vestuário",
    "riachuelo": "Vestuário", "hering": "Vestuário", "marisa": "Vestuário",

    # Salário
    "salario": "Salário", "pagamento": "Salário", "folha": "Salário",
    "prolabore": "Salário",

    # Assinaturas
    "assinatura": "Assinaturas", "mensalidade": "Assinaturas",

    # Viagens
    "hotel": "Viagens", "pousada": "Viagens", "airbnb": "Viagens",
    "booking": "Viagens", "decolar": "Viagens", "latam": "Viagens",
    "gol": "Viagens", "azul": "Viagens", "tam": "Viagens",
    "passagem aerea": "Viagens",

    # Pets
    "pet shop": "Pets", "veterinario": "Pets", "racao": "Pets",

    # Investimentos
    "tesouro direto": "Renda Fixa", "cdb": "Renda Fixa", "lci": "Renda Fixa",
    "lca": "Renda Fixa", "fundo": "Fundos", "acoes": "Renda Variável",
    "bitcoin": "Criptomoedas", "cripto": "Criptomoedas",
}


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class CategorizationService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def suggest_category(self, description: str) -> dict:
        """
        Sugere categoria para uma descrição de transação.
        Retorna: {category_id, category_name, confidence, source}
        """
        normalized = normalize_text(description)

        # 1. Exact match from user learning
        result = await self.db.execute(
            select(CategoryLearning, Category)
            .join(Category, CategoryLearning.category_id == Category.id)
            .where(
                CategoryLearning.user_id == self.user_id,
                CategoryLearning.pattern == description.strip().upper()[:200],
            )
        )
        row = result.first()
        if row:
            learning, category = row
            return {
                "category_id": category.id,
                "category_name": category.name,
                "confidence": float(learning.confidence),
                "source": "historico",
            }

        # 2. Fuzzy match from user learning (trigram similarity)
        learning_result = await self.db.execute(
            select(CategoryLearning, Category)
            .join(Category, CategoryLearning.category_id == Category.id)
            .where(CategoryLearning.user_id == self.user_id)
            .order_by(CategoryLearning.usage_count.desc())
            .limit(100)
        )
        learning_rows = learning_result.all()

        best_match = None
        best_score = 0.0

        if learning_rows:
            from difflib import SequenceMatcher
            for learning, category in learning_rows:
                score = SequenceMatcher(None, normalized, normalize_text(learning.pattern)).ratio()
                if score > best_score:
                    best_score = score
                    best_match = (learning, category)

            if best_score >= 0.75 and best_match:
                return {
                    "category_id": best_match[1].id,
                    "category_name": best_match[1].name,
                    "confidence": best_score,
                    "source": "similaridade",
                }

        # 3. Keyword rules
        for keyword, category_name in KEYWORD_RULES.items():
            if keyword in normalized:
                cat_result = await self.db.execute(
                    select(Category).where(
                        Category.name == category_name,
                        (Category.user_id == self.user_id) | (Category.is_system == True),
                    )
                )
                cat = cat_result.scalar_one_or_none()
                if cat:
                    return {
                        "category_id": cat.id,
                        "category_name": cat.name,
                        "confidence": 0.85,
                        "source": "regras",
                    }

        # 4. No suggestion - ask user
        return {
            "category_id": None,
            "category_name": None,
            "confidence": 0.0,
            "source": "sem_sugestao",
            "needs_review": True,
        }

    async def categorize_batch(self, descriptions: List[str]) -> List[dict]:
        """Categoriza uma lista de descrições."""
        return [await self.suggest_category(d) for d in descriptions]

    async def detect_installments(self, description: str) -> Optional[Dict]:
        """Detecta padrões de parcelamento."""
        patterns = [
            r"(\d+)[/\-](\d+)",  # 3/10, 3-10
            r"parcela\s+(\d+)\s+de\s+(\d+)",  # parcela 3 de 10
            r"(\d+)\s+de\s+(\d+)",  # 3 de 10
            r"parc\s*(\d+)/(\d+)",  # parc3/10
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                if 1 <= current <= total <= 120:
                    return {"current": current, "total": total}
        return None

    async def detect_subscriptions(self, transactions: list) -> List[dict]:
        """
        Detecta assinaturas recorrentes em uma lista de transações.
        Agrupa por descrição normalizada e verifica frequência.
        """
        from collections import defaultdict
        import statistics

        groups = defaultdict(list)
        for t in transactions:
            key = normalize_text(t.get("description", ""))[:50]
            groups[key].append(t)

        subscriptions = []
        for key, group in groups.items():
            if len(group) < 2:
                continue

            amounts = [t["amount"] for t in group]
            dates = sorted([t["date"] for t in group])

            # Check if amounts are consistent
            if max(amounts) - min(amounts) > max(amounts) * 0.05:  # 5% tolerance
                continue

            # Check intervals
            if len(dates) >= 2:
                intervals = []
                for i in range(1, len(dates)):
                    delta = (dates[i] - dates[i - 1]).days
                    intervals.append(delta)

                avg_interval = statistics.mean(intervals)
                if len(intervals) > 1:
                    std_interval = statistics.stdev(intervals)
                    if std_interval > 10:  # Too variable
                        continue

                # Classify frequency
                if 25 <= avg_interval <= 35:
                    frequency = 30
                elif 6 <= avg_interval <= 8:
                    frequency = 7
                elif 13 <= avg_interval <= 16:
                    frequency = 14
                elif 360 <= avg_interval <= 370:
                    frequency = 365
                else:
                    continue

                subscriptions.append({
                    "name": group[0].get("description", key),
                    "amount": statistics.mean(amounts),
                    "frequency_days": frequency,
                    "occurrences": len(group),
                    "transaction_ids": [t.get("id") for t in group],
                })

        return subscriptions
