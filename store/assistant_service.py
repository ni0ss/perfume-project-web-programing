"""Ground the local intent classifier's answers in the current store catalogue."""

import json
import os
import ast
import operator
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from .assistant_ml import MODEL_VERSION, classify_with_domain_cues, detect_language, normalize_text, rank_products


LOCAL_MODELS = {
    "qwen2.5:1.5b": "Qwen 2.5 (خفيف)",
    "qwen2.5:3b": "Qwen 2.5 (أقوى)",
}
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ARITHMETIC_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _answer_arithmetic(message, language):
    """Safely evaluate a simple numeric expression without asking an LLM."""
    expression = normalize_text(message).translate(ARABIC_DIGITS)
    replacements = (
        (r"\b(?:multiplied\s+by|multiply|times)\b|ضرب|\bفي\b", " * "),
        (r"\b(?:divided\s+by|divide(?:d)?)\b|قسمة(?:\s+على)?", " / "),
        (r"\b(?:plus|add(?:ed)?(?:\s+to)?)\b|زائد|جمع", " + "),
        (r"\b(?:minus|subtract(?:ed)?(?:\s+from)?)\b|ناقص|طرح", " - "),
    )
    for pattern, replacement in replacements:
        expression = re.sub(pattern, replacement, expression, flags=re.IGNORECASE)
    expression = re.sub(
        r"\b(?:what\s+is|what's|calculate|compute|how\s+much\s+is|equals?|result|show|answer)\b|كم\s+يساوي|ما\s+ناتج|احسب|الناتج|يساوي",
        " ", expression, flags=re.IGNORECASE,
    )
    expression = expression.replace("×", "*").replace("÷", "/").replace("−", "-")
    expression = re.sub(r"[^0-9.+*/()\-\s]", " ", expression)
    expression = expression.strip().rstrip(".").strip()
    if not expression or not re.search(r"[+*/-]", expression) or len(expression) > 120:
        return None

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC_OPERATORS:
            return ARITHMETIC_OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        raise ValueError("unsupported arithmetic expression")

    try:
        result = evaluate(ast.parse(expression, mode="eval"))
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"الناتج هو {result}." if language == "ar" else f"The result is {result}."


def _ask_local_model(message, language, model, products):
    """Ask Ollama without sending the prompt outside the local machine."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    selected_model = model if model in LOCAL_MODELS else os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    if selected_model not in LOCAL_MODELS:
        selected_model = "qwen2.5:3b"
    language_instruction = (
        "أجب باللغة العربية الواضحة وباختصار. للمعلومات العامة، لا تخترع حقائق أو مصطلحات؛ إذا لم تكن متأكدًا فقل ذلك."
        if language == "ar" else
        "Answer clearly and concisely in English. For general facts, do not invent details or terminology; say when you are unsure."
    )
    catalogue = "\n".join(
        f"- {item.name} / {item.name_en or item.name}: {item.description} / {item.description_en or item.description}; SAR {item.price:.2f}; stock {item.stock}"
        for item in products
    ) or "No products are currently available."
    payload = {
        "model": selected_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": (
                "You are a helpful local assistant inside PERFUME. Answer everyday general questions. "
                "For shop-specific facts, use only the supplied catalogue context; "
                "if the context does not contain the answer, say you do not know. Never invent prices, stock, or contact details. "
                + language_instruction + "\nCurrent in-stock shop catalogue:\n" + catalogue
            )},
            {"role": "user", "content": message},
        ],
        "options": {"temperature": 0.1, "num_predict": 220},
    }
    request = Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        try:
            request_timeout = max(10, int(os.environ.get("OLLAMA_REQUEST_TIMEOUT_SECONDS", "120")))
        except ValueError:
            request_timeout = 120
        with urlopen(request, timeout=request_timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result.get("message", {}).get("content", "").strip()
        if answer:
            return answer, selected_model
    except (URLError, TimeoutError, OSError, ValueError, KeyError):
        pass
    return None, selected_model


def answer_store_question(message, requested_language, products, requested_model=None):
    # Follow the language the visitor actually uses, even when the page itself
    # is currently set to the other language.
    language = "ar" if detect_language(message) == "ar" else (requested_language if requested_language in ("ar", "en") else "en")
    normalized_query = normalize_text(message)
    arithmetic_answer = _answer_arithmetic(message, language)
    # Use explicit, high precision store cues for fixed catalogue answers. The
    # old Naive Bayes fallback guessed a shop intent for unrelated questions;
    # everything it cannot confidently recognize now reaches the local LLM.
    intent = "math" if arithmetic_answer is not None else (classify_with_domain_cues(message, language) or "other")
    products = list(products)

    def product_name(product):
        return product.name if language == "ar" else (product.name_en or product.name)

    def details(items):
        if not items:
            return "لا توجد عطور متاحة حالياً." if language == "ar" else "No perfumes are currently available."
        return "\n".join(f"• {product_name(item)} — SAR {item.price:.2f}" for item in items)

    named_product = next(
        (
            product for product in products
            if normalize_text(product.name) in normalized_query
            or (product.name_en and normalize_text(product.name_en) in normalized_query)
        ),
        None,
    )

    if intent == "math":
        answer = arithmetic_answer
    elif intent == "price":
        selected = [named_product] if named_product else products
        if named_product:
            answer = f"{product_name(named_product)}: SAR {named_product.price:.2f}."
        elif language == "ar":
            answer = f"أسعار العطور المتوفرة:\n{details(selected)}"
        else:
            answer = f"Here are the available perfume prices:\n{details(selected)}"
    elif intent == "delivery_order":
        answer = (
            "هذا متجر تجريبي. يمكنك إرسال طلب تجريبي، ولا يتم تحصيل أي مبلغ. الشحن مجاني في النسخة الحالية، ولا يوجد تتبع مباشر للشحنات."
            if language == "ar"
            else "This is a demo store. You can place a test order, and no money is collected. Shipping is free in this version; live shipment tracking is not available."
        )
    elif intent == "contact":
        answer = (
            "بيانات التواصل مع هذا المتجر التجريبي غير مهيأة بعد. يرجى مراجعة قسم التواصل أسفل الصفحة."
            if language == "ar"
            else "Contact details for this demo store have not been configured. Please see the Contact section at the bottom of the page."
        )
    elif intent == "recommendation":
        selected = rank_products(products, message)[:3]
        answer = (
            f"أقترح عليك هذه العطور من مجموعتنا:\n{details(selected)}"
            if language == "ar"
            else f"Based on your preferences, consider:\n{details(selected)}"
        )
    elif intent == "catalog":
        answer = (
            f"هذه العطور المتوفرة في مجموعتنا:\n{details(products)}"
            if language == "ar"
            else f"Here are the perfumes in our collection:\n{details(products)}"
        )
    elif intent == "store_info":
        answer = (
            "هذا متجر عطور تجريبي يعرض المنتجات والأسعار ومعلوماتها. يمكنك إضافة المنتجات إلى السلة وإرسال طلب تجريبي من دون تحصيل أموال."
            if language == "ar"
            else "This is a demo perfume store. It shows product details and prices and lets you place a test order without collecting money."
        )
    elif intent == "product_info":
        if named_product:
            description = named_product.description if language == "ar" else (named_product.description_en or named_product.description)
            answer = (
                f"{product_name(named_product)}: {description} السعر: SAR {named_product.price:.2f}."
                if language == "ar"
                else f"{product_name(named_product)}: {description} Price: SAR {named_product.price:.2f}."
            )
        else:
            answer = (
                f"هذه العطور المتوفرة في مجموعتنا:\n{details(products)}"
                if language == "ar"
                else f"Here are the perfumes in our collection:\n{details(products)}"
            )
    elif intent == "greeting":
        answer = (
            "مرحباً بك في PERFUME! أستطيع مساعدتك في معرفة الأسعار، واستعراض العطور، أو اختيار عطر مناسب."
            if language == "ar"
            else "Welcome to PERFUME! I can help with prices, browsing the collection, or choosing a fragrance."
        )
    else:
        intent = "other"
        answer, selected_model = _ask_local_model(message, language, requested_model, products)
        if answer is None:
            answer = (
                "المساعد الذكي المحلي غير جاهز الآن. أقدر أساعدك بمعلومات العطور والأسعار والتوصيل."
                if language == "ar"
                else "The local AI is not ready right now. I can still help with perfumes, prices, and delivery."
            )

    return {
        "answer": answer,
        "intent": intent,
        "classifier": MODEL_VERSION,
        "assistant_model": selected_model if intent == "other" else ("local-arithmetic" if intent == "math" else "store-catalog"),
    }
