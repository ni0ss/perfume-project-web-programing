"""Ground the local intent classifier's answers in the current store catalogue."""

from .assistant_ml import MODEL_VERSION, classify_intent, normalize_text, rank_products


def answer_store_question(message, requested_language, products):
    has_arabic = any("\u0600" <= character <= "\u06ff" for character in message)
    language = requested_language if requested_language in ("ar", "en") else ("ar" if has_arabic else "en")
    normalized_query = normalize_text(message)
    intent, _ = classify_intent(message)
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

    if intent == "price":
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
            "تقدر تتواصل معنا على الرقم +966 50 123 4567 أو البريد Naif7iqul@gmail.com."
            if language == "ar"
            else "You can contact us at +966 50 123 4567 or Naif7iqul@gmail.com."
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
        answer = (
            "أقدر أساعدك في معلومات متجر PERFUME، مثل العطور والأسعار والتوصيل. اسألني عن أحد هذه الأمور."
            if language == "ar"
            else "I can help with PERFUME store information, such as fragrances, prices, and delivery. Please ask about one of these topics."
        )

    return {
        "answer": answer,
        "intent": intent,
        "classifier": MODEL_VERSION,
    }
