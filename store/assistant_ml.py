"""Small, locally trained intent classifier for the PERFUME store assistant.

This module deliberately uses only the Python standard library. It classifies
the request; answers are then rendered from verified store data and templates.
It does not generate free-form text or call an external service.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path


MODEL_VERSION = "local-hybrid-nb-2.1"
TRAINING_PATH = Path(__file__).parent / "data" / "intent_training.json"
ARABIC_TRANSLATION = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي",
    "ؤ": "و", "ئ": "ي",
})
TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0621-\u064a]+", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Normalize common Arabic orthographic forms and English case/punctuation."""
    normalized = unicodedata.normalize("NFKC", str(text)).casefold().translate(ARABIC_TRANSLATION)
    normalized = "".join(
        character for character in normalized
        if character != "ـ" and unicodedata.category(character) not in {"Mn", "Me"}
    )
    return normalized


def _base_tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text))


def tokenize(text: str) -> list[str]:
    tokens = _base_tokens(text)
    expanded = []
    for token in tokens:
        expanded.append(token)
        if not token or not ("\u0621" <= token[0] <= "\u064a"):
            continue
        # Arabic conjunctions and prepositions can be stacked with the article,
        # e.g. وبالعطر and للزائر. Explore a small bounded set of valid
        # prefixes so those forms share features with their base words.
        candidates = [token]
        seen = {token}
        frontier = [token]
        prefixes = ("ال", "و", "ف", "ب", "ك", "ل")
        while frontier:
            current = frontier.pop()
            for prefix in prefixes:
                if current.startswith(prefix) and len(current) - len(prefix) >= 3:
                    stripped = current[len(prefix):]
                    if stripped not in seen:
                        seen.add(stripped)
                        candidates.append(stripped)
                        frontier.append(stripped)
        expanded.extend(candidate for candidate in candidates if candidate != token)
    return expanded


def _features(text: str, char_weight: float = 0.0) -> Counter[str]:
    words = _base_tokens(text)
    expanded_words = tokenize(text)
    features = Counter(expanded_words)
    features.update({f"{left}::{right}": 0.5 for left, right in zip(words, words[1:])})
    if char_weight > 0:
        for word in expanded_words:
            padded = f"^{word}$"
            grams = [
                (size, padded[index:index + size])
                for size in (2, 3, 4)
                for index in range(max(0, len(padded) - size + 1))
            ]
            if grams:
                contribution = char_weight / len(grams)
                for size, gram in grams:
                    features[f"char{size}:{gram}"] += contribution
    return features


class MultinomialNaiveBayes:
    """A compact multinomial Naive Bayes text classifier with Laplace smoothing."""

    def __init__(self, alpha: float = 1.0, char_weight: float = 0.0) -> None:
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        self.alpha = alpha
        self.char_weight = char_weight
        self.classes: tuple[str, ...] = ()
        self.vocabulary: set[str] = set()
        self.document_counts: Counter[str] = Counter()
        self.feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.feature_totals: Counter[str] = Counter()
        self.document_total = 0

    def fit(self, examples: list[dict[str, str]]) -> "MultinomialNaiveBayes":
        if not examples:
            raise ValueError("training data must not be empty")
        for example in examples:
            text = str(example["text"])
            label = str(example["intent"])
            features = _features(text, self.char_weight)
            self.classes = tuple(sorted(set(self.classes) | {label}))
            self.document_counts[label] += 1
            self.document_total += 1
            for feature, count in features.items():
                self.vocabulary.add(feature)
                self.feature_counts[label][feature] += count
                self.feature_totals[label] += count
        if not self.vocabulary:
            raise ValueError("training data contains no usable tokens")
        return self

    def predict_scores(self, text: str) -> dict[str, float]:
        if not self.classes:
            raise RuntimeError("classifier must be fitted before prediction")
        features = _features(text, self.char_weight)
        vocabulary_size = len(self.vocabulary)
        scores: dict[str, float] = {}
        for label in self.classes:
            prior = self.document_counts[label] / self.document_total
            denominator = self.feature_totals[label] + self.alpha * vocabulary_size
            score = math.log(prior)
            for feature, count in features.items():
                if feature in self.vocabulary:
                    probability = (self.feature_counts[label][feature] + self.alpha) / denominator
                    score += count * math.log(probability)
            scores[label] = score
        return scores

    def predict(self, text: str) -> tuple[str, float]:
        scores = self.predict_scores(text)
        label = max(self.classes, key=lambda candidate: (scores[candidate], candidate))
        max_score = max(scores.values())
        exponentials = {key: math.exp(value - max_score) for key, value in scores.items()}
        normalized_score = exponentials[label] / sum(exponentials.values())
        return label, normalized_score


class TfidfNearestNeighbor:
    """A local TF-IDF cosine classifier used as a candidate model for validation."""

    def __init__(self, neighbors: int = 3, char_weight: float = 0.15) -> None:
        self.neighbors = neighbors
        self.char_weight = char_weight
        self.idf: dict[str, float] = {}
        self.documents: list[tuple[str, dict[str, float]]] = []
        self.classes: tuple[str, ...] = ()

    @staticmethod
    def _normalize(vector: dict[str, float]) -> dict[str, float]:
        norm = math.sqrt(sum(value * value for value in vector.values()))
        return {feature: value / norm for feature, value in vector.items()} if norm else {}

    def fit(self, examples: list[dict[str, str]]) -> "TfidfNearestNeighbor":
        if not examples:
            raise ValueError("training data must not be empty")
        raw_documents = [_features(example["text"], self.char_weight) for example in examples]
        document_frequency: Counter[str] = Counter()
        for document in raw_documents:
            document_frequency.update(document.keys())
        count = len(raw_documents)
        self.idf = {
            feature: math.log((count + 1) / (frequency + 1)) + 1
            for feature, frequency in document_frequency.items()
        }
        self.documents = []
        for example, raw in zip(examples, raw_documents):
            vector = self._normalize({feature: count * self.idf[feature] for feature, count in raw.items()})
            self.documents.append((example["intent"], vector))
        self.classes = tuple(sorted({example["intent"] for example in examples}))
        return self

    def predict_scores(self, text: str) -> dict[str, float]:
        query = _features(text, self.char_weight)
        vector = self._normalize({feature: count * self.idf[feature] for feature, count in query.items() if feature in self.idf})
        similarities = []
        for label, document in self.documents:
            similarity = sum(value * document.get(feature, 0.0) for feature, value in vector.items())
            similarities.append((similarity, label))
        scores = {label: 0.0 for label in self.classes}
        for similarity, label in sorted(similarities, reverse=True)[:self.neighbors]:
            scores[label] += max(0.0, similarity)
        return scores

    def predict(self, text: str) -> tuple[str, float]:
        scores = self.predict_scores(text)
        label = max(self.classes, key=lambda candidate: (scores[candidate], candidate))
        total = sum(scores.values())
        return label, scores[label] / total if total else 0.0


def load_training_examples(language: str | None = None) -> list[dict[str, str]]:
    payload = json.loads(TRAINING_PATH.read_text(encoding="utf-8"))
    examples = []
    for intent, language_groups in payload.items():
        for example_language, phrases in language_groups.items():
            if language is not None and language != example_language:
                continue
            examples.extend({"text": phrase, "intent": intent, "language": example_language} for phrase in phrases)
    return examples


@lru_cache(maxsize=2)
def get_classifier(language: str) -> MultinomialNaiveBayes:
    examples = load_training_examples(language)
    return MultinomialNaiveBayes(alpha=1.0, char_weight=0.15).fit(examples)


def detect_language(text: str) -> str:
    return "ar" if any("\u0600" <= character <= "\u06ff" for character in text) else "en"


def classify_intent(text: str, language: str | None = None) -> tuple[str, float]:
    selected_language = language if language in ("ar", "en") else detect_language(text)
    nb_label, nb_score = get_classifier(selected_language).predict(text)
    cue_label = classify_with_domain_cues(text, selected_language)
    return (cue_label, nb_score) if cue_label else (nb_label, nb_score)


def classify_with_domain_cues(text: str, language: str) -> str | None:
    """Use a small explicit cue layer for high-value store intents.

    The learned classifier remains the fallback for paraphrases. These cues
    reduce predictable confusions when product words dominate the question.
    """
    normalized = normalize_text(text)
    tokens = set(tokenize(text))
    arabic = language == "ar"

    def has_any(words: set[str]) -> bool:
        normalized_words = {normalize_text(word) for word in words}
        return bool(tokens & normalized_words)

    domain_terms = (
        {"perfume", "perfumes", "fragrance", "fragrances", "scent", "scents", "musk", "oud", "amber", "rose", "citrus", "product", "products", "collection", "عطر", "عطور", "مسك", "عود", "عنبر", "ورد", "حمضيات", "عطور", "مجموعة"}
    )
    has_domain = has_any(domain_terms)

    order_terms = (
        {"order", "orders", "ordering", "delivery", "deliver", "delivered", "shipping", "ship", "shipment", "tracking", "track", "checkout", "purchase", "buy", "bought", "payment", "pay", "اطلب", "طلب", "الطلب", "طلبات", "شراء", "اشتري", "اشتر", "توصيل", "يوصل", "وصل", "شحن", "الشحن", "شحنة", "السلة", "دفع", "استلام"}
    )
    contact_terms = (
        {"contact", "reach", "message", "email", "phone", "telephone", "call", "support", "customer", "service", "helpdesk", "channel", "speak", "talk", "connect", "اتواصل", "تواصل", "اكلم", "كلم", "رقم", "هاتف", "البريد", "ايميل", "اتصال", "رسالة", "راسل", "مراسل", "موظف", "دعم", "العملاء", "خدمة", "استفسار", "واتساب"}
    )
    price_terms = (
        {"price", "prices", "pricing", "cost", "costs", "amount", "value", "charge", "charges", "fee", "fees", "rate", "rates", "riyals", "sar", "سعر", "السعر", "اسعار", "الاسعار", "ثمن", "قيمة", "تكلفة", "يكلف", "مبلغ", "ريال", "بكم"}
    )
    explicit_recommendation_terms = (
        {"recommend", "recommendation", "suggest", "choose", "pick", "prefer", "suitable", "suits", "looking", "find", "drawn", "رشح", "رشحلي", "اقترح", "اختار", "اختاري", "افضل", "تناسب", "يناسب", "مناسب", "مناسبة", "دلني", "ابحث", "اختيار", "اميل"}
    )
    preference_terms = (
        {"like", "love", "want", "need", "احب", "تحب", "ابي", "ابغى", "احتاج"}
    )
    product_info_terms = (
        {"describe", "description", "details", "detail", "notes", "smell", "scent", "profile", "composition", "ingredients", "about", "tell", "information", "معلومات", "وصف", "صف", "تركيبة", "مكونات", "نفحات", "ريحة", "رائحة", "تفاصيل", "حدثني", "احكي", "اشرح", "يميز"}
    )
    explicit_detail_terms = (
        {"describe", "description", "details", "detail", "smell", "profile", "composition", "ingredients", "about", "tell", "information", "معلومات", "وصف", "صف", "تركيبة", "مكونات", "ريحة", "رائحة", "تفاصيل", "حدثني", "احكي", "اشرح", "يميز"}
    )
    catalog_terms = (
        {"list", "browse", "display", "show", "see", "view", "offer", "have", "available", "availability", "stock", "range", "options", "choices", "catalog", "collection", "products", "items", "scents", "fragrances", "all", "العطور", "عطور", "منتجات", "المنتجات", "اصناف", "خيارات", "قائمة", "تشكيلة", "معروض", "المعروض", "متوفر", "متوفرة", "موجود", "الموجود", "عندكم", "ورني", "اعرض", "عرض", "اتصفح", "كل"}
    )
    store_info_terms = (
        {"purpose", "goal", "idea", "project", "prototype", "demo", "platform", "website", "site", "application", "store", "shop", "الغرض", "هدف", "فكرة", "مشروع", "تجريبي", "نموذج", "منصة", "موقع", "المتجر", "التطبيق", "الخدمات", "يقدم", "وظيفة", "الغرض", "زائر"}
    )
    out_of_scope_terms = (
        {"weather", "equation", "math", "poem", "poetry", "match", "game", "recipe", "cook", "cooking", "distance", "earth", "mars", "طقس", "معادلة", "رياضيات", "قصيدة", "شعر", "مباراة", "كبسة", "اطبخ", "طبخ", "وصفة", "دجاج", "عدس", "الارض", "المريخ"}
    )

    if has_any(out_of_scope_terms):
        return "other"

    # Explicit transaction and price requests outrank descriptive product nouns.
    if has_any(order_terms):
        return "delivery_order"
    if has_any(contact_terms):
        return "contact"
    if has_any(price_terms):
        return "price"
    if has_any(store_info_terms) and (has_domain or has_any({"purpose", "goal", "idea", "project", "prototype", "demo", "الغرض", "هدف", "فكرة", "مشروع", "تجريبي", "نموذج"})):
        return "store_info"
    if has_any(explicit_recommendation_terms) and has_domain:
        return "recommendation"
    if has_any(preference_terms) and has_domain and not has_any(explicit_detail_terms):
        return "recommendation"
    if has_any(product_info_terms) and has_domain:
        return "product_info"
    if has_any(catalog_terms) and (has_domain or has_any({"browse", "options", "choices", "catalog", "list", "scents", "fragrances", "see", "view", "عطور", "منتجات", "خيارات", "قائمة", "تشكيلة", "اتصفح", "ورني", "اعرض"})):
        return "catalog"

    greeting_phrases = (
        "hello", "hi there", "hey", "greetings", "good morning", "good afternoon", "good evening",
        "nice to meet", "pleased to meet", "how are you", "how is everyone", "hope your day",
        "السلام", "مرحبا", "اهلا", "اهلين", "هلا", "يا هلا", "حيا الله", "عساكم بخير", "صباح الخير", "مساء الخير", "مساء الورد", "صباح الورد",
    )
    if any(phrase in normalized for phrase in greeting_phrases):
        return "greeting"

    # Common inflected forms of Arabic delivery verbs.
    if arabic and any(token.startswith(("توصل", "وصل")) for token in tokens):
        return "delivery_order"

    # Catch simple inventory questions where the catalog noun is implicit.
    if has_any({"inventory", "العطور", "منتجات"}) and has_any(catalog_terms):
        return "catalog"
    return None


PREFERENCE_TERMS: dict[str, set[str]] = {
    "rose": {"rose", "floral", "ورد", "وردي", "زهري", "جوري"},
    "musk": {"musk", "clean", "daily", "مسك", "نظيف", "يومي"},
    "oud": {"oud", "wood", "woody", "عود", "خشبي"},
    "amber": {"amber", "warm", "عنبري", "عنبر", "دافئ"},
    "citrus": {"citrus", "fresh", "bergamot", "حمضيات", "منعش", "برغموت"},
    "evening": {"evening", "night", "occasion", "مساء", "ليلي", "مناسبة"},
}


def matching_preferences(text: str) -> set[str]:
    query_tokens = set(tokenize(text))
    return {
        profile for profile, terms in PREFERENCE_TERMS.items()
        if any(tokenize(term)[0] in query_tokens for term in terms)
    }


def rank_products(products, query: str):
    """Rank in-stock products by overlap with bilingual scent-profile terms."""
    preferences = matching_preferences(query)
    scored = []
    for product in products:
        searchable = " ".join((
            product.name,
            product.name_en,
            product.description,
            product.description_en,
        ))
        product_tokens = set(tokenize(searchable))
        score = sum(
            1 for profile in preferences
            if any(tokenize(term)[0] in product_tokens for term in PREFERENCE_TERMS[profile])
        )
        if not preferences or score:
            scored.append((score, product))
    scored.sort(key=lambda item: (-item[0], item[1].price, item[1].pk or 0))
    return [product for _, product in scored]
