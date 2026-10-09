"""Reproducible comparison of the original rules and local Naive Bayes model.

Run from the repository root with: python research/evaluate_intents.py
The evaluation phrases are author-composed and are not customer conversations.
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from store.assistant_ml import MODEL_VERSION, classify_intent  # noqa: E402
from store.models import Product  # noqa: E402


LABELS = (
    "catalog", "contact", "delivery_order", "greeting", "other", "price",
    "product_info", "recommendation", "store_info",
)
TEST_PATH = ROOT / "research" / "intent_test.json"
TRAIN_PATH = ROOT / "store" / "data" / "intent_training.json"
RESULTS_PATH = ROOT / "research" / "results.json"


def original_rule_baseline(message: str, products: list[Product]) -> str:
    """Reproduce the pre-study substring-rule priority for intent comparison."""
    query = message.casefold()

    if any(term in query for term in (
        "price", "cost", "how much", "كم السعر", "السعر", "بكم", "أسعار", "الاسعار",
    )):
        return "price"
    if any(term in query for term in (
        "order", "delivery", "shipping", "payment", "checkout", "طلب", "توصيل", "شحن", "دفع", "السلة",
    )):
        return "delivery_order"
    if any(term in query for term in (
        "contact", "email", "phone", "call", "تواصل", "البريد", "ايميل", "إيميل", "رقم الجوال", "رقم الهاتف",
    )):
        return "contact"

    categories = (
        ("rose", "floral", "ورد", "زهري"),
        ("musk", "clean", "daily", "مسك", "يومي", "نظيف"),
        ("oud", "amber", "warm", "evening", "عود", "عنبر", "مساء", "دافئ"),
        ("citrus", "fresh", "bergamot", "حمضيات", "منعش", "برغموت"),
    )
    available = [product for product in products if product.available and product.stock > 0]
    for terms in categories:
        if any(term in query for term in terms):
            if any(
                any(term in " ".join((p.name, p.name_en, p.description, p.description_en)).casefold() for term in terms)
                for p in available
            ):
                return "recommendation"
            break

    if any(term in query for term in (
        "perfume", "perfumes", "products", "collection", "recommend", "suggest", "عطر", "عطور", "منتج", "منتجات", "المجموعة",
    )):
        return "catalog"
    if any(term in query for term in (
        "about the store", "what is this site", "about perfume", "عن المتجر", "عن الموقع", "ايش يقدم", "ماذا يقدم",
    )):
        return "store_info"
    if any(
        p.name.casefold() in query or (p.name_en and p.name_en.casefold() in query)
        for p in available
    ):
        return "product_info"
    if any(term in query for term in ("hello", "hi", "السلام عليكم", "مرحبا", "هلا")):
        return "greeting"
    return "other"


def scores(expected: list[str], predicted: list[str], labels: tuple[str, ...]) -> dict:
    total = len(expected)
    accuracy = sum(left == right for left, right in zip(expected, predicted)) / total if total else 0.0
    per_class = {}
    for label in labels:
        true_positive = sum(a == label and b == label for a, b in zip(expected, predicted))
        false_positive = sum(a != label and b == label for a, b in zip(expected, predicted))
        false_negative = sum(a == label and b != label for a, b in zip(expected, predicted))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(a == label for a in expected)}
    return {
        "accuracy": accuracy,
        "macro_precision": statistics.mean(row["precision"] for row in per_class.values()),
        "macro_recall": statistics.mean(row["recall"] for row in per_class.values()),
        "macro_f1": statistics.mean(row["f1"] for row in per_class.values()),
        "per_class": per_class,
    }


def evaluate() -> dict:
    cases = json.loads(TEST_PATH.read_text(encoding="utf-8"))
    training = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    products = list(Product.objects.all())
    expected = [case["intent"] for case in cases]
    nb_predictions = [classify_intent(case["text"])[0] for case in cases]
    rule_predictions = [original_rule_baseline(case["text"], products) for case in cases]

    language_results = {}
    for language in ("ar", "en"):
        selected = [index for index, case in enumerate(cases) if case["language"] == language]
        language_results[language] = {
            "test_examples": len(selected),
            "naive_bayes": scores([expected[i] for i in selected], [nb_predictions[i] for i in selected], LABELS),
            "rule_baseline": scores([expected[i] for i in selected], [rule_predictions[i] for i in selected], LABELS),
        }

    latency_ms = []
    for case in cases:
        for _ in range(10):
            started = time.perf_counter_ns()
            classify_intent(case["text"])
            latency_ms.append((time.perf_counter_ns() - started) / 1_000_000)

    confusion = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for actual, predicted in zip(expected, nb_predictions):
        confusion[actual][predicted] += 1

    result = {
    "study": "Author-composed held-out bilingual intent benchmark; no customer conversations or human participants.",
        "model": MODEL_VERSION,
        "training_examples": sum(len(phrases) for by_language in training.values() for phrases in by_language.values()),
        "training_counts_by_intent_and_language": {
            intent: {language: len(phrases) for language, phrases in by_language.items()}
            for intent, by_language in training.items()
        },
        "test_examples": len(cases),
        "test_counts_by_intent": dict(Counter(expected)),
        "overall": {
            "naive_bayes": scores(expected, nb_predictions, LABELS),
            "rule_baseline": scores(expected, rule_predictions, LABELS),
        },
        "by_language": language_results,
        "naive_bayes_confusion_matrix": confusion,
        "classifier_latency_ms": {
            "measurement": "single local Python process; 10 repeated predictions per authored query; classifier only",
            "median": statistics.median(latency_ms),
            "p95": sorted(latency_ms)[int(0.95 * (len(latency_ms) - 1))],
        },
        "environment": {"python": platform.python_version(), "django": django.get_version()},
        "notes": [
            "The benchmark was authored by the project team and is not a sample of real customer language.",
            "The reported normalized scores are not a user-satisfaction measure.",
            "The result is an internal reproducible evaluation and does not imply journal acceptance.",
        ],
    }
    RESULTS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    evaluate()
