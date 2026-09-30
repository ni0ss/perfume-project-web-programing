from rest_framework import permissions, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.reverse import reverse

from .models import Order, Product, StoreContent
from .serializers import AdminOrderSerializer, ProductSerializer, StoreContentSerializer


@api_view(("GET",))
@permission_classes((permissions.AllowAny,))
def api_root(request):
    links = {
        "products": reverse("api-product-list", request=request),
        "store_content": reverse("api-store-content", request=request),
        "assistant": reverse("api-assistant", request=request),
    }
    if request.user.is_staff:
        links["orders"] = reverse("api-order-list", request=request)
    return Response(links)


class ProductViewSet(viewsets.ModelViewSet):
    """Public read access; staff-only product changes from the dashboard."""

    serializer_class = ProductSerializer
    authentication_classes = (SessionAuthentication,)
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def get_queryset(self):
        products = Product.objects.order_by("-created_at")
        if self.request.user.is_staff:
            return products
        return products.filter(available=True, stock__gt=0)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            permission_classes = (permissions.AllowAny,)
        else:
            permission_classes = (permissions.IsAdminUser,)
        return [permission() for permission in permission_classes]


class AdminOrderViewSet(viewsets.ModelViewSet):
    """Staff can view orders and update their status through the REST API."""

    queryset = Order.objects.select_related("user").prefetch_related("items")
    serializer_class = AdminOrderSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)
    http_method_names = ("get", "head", "options", "put", "patch")


class StoreContentView(RetrieveUpdateAPIView):
    serializer_class = StoreContentSerializer
    authentication_classes = (SessionAuthentication,)

    def get_object(self):
        return StoreContent.get_solo()

    def get_permissions(self):
        permission_class = permissions.AllowAny if self.request.method == "GET" else permissions.IsAdminUser
        return [permission_class()]


class LocalAssistantView(APIView):
    """A small on-site assistant that uses only the local product catalogue and rules."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request):
        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"error": "Please enter a question."}, status=400)
        if len(message) > 500:
            return Response({"error": "Please keep your question under 500 characters."}, status=400)

        requested_language = request.data.get("language")
        has_arabic = any("\u0600" <= character <= "\u06ff" for character in message)
        language = requested_language if requested_language in ("ar", "en") else ("ar" if has_arabic else "en")
        query = message.casefold()
        products = list(Product.objects.filter(available=True, stock__gt=0).order_by("price", "name"))

        def product_name(product):
            return product.name if language == "ar" else (product.name_en or product.name)

        def details(items):
            return "\n".join(
                f"• {product_name(item)} — SAR {item.price:.2f}"
                for item in items
            )

        price_question = any(term in query for term in (
            "price", "cost", "how much", "كم السعر", "السعر", "بكم", "أسعار", "الاسعار",
        ))
        order_question = any(term in query for term in (
            "order", "delivery", "shipping", "payment", "checkout", "طلب", "توصيل", "شحن", "دفع", "السلة",
        ))
        if price_question:
            answer = (
                f"أسعار العطور المتوفرة:\n{details(products)}"
                if language == "ar"
                else f"Here are the prices of our available perfumes:\n{details(products)}"
            )
            return Response({"answer": answer})

        if order_question:
            answer = (
                "هذا متجر تجريبي. يمكنك إرسال طلب تجريبي، ولا يتم تحصيل أي مبلغ. رسوم الشحن الحالية صفر."
                if language == "ar"
                else "This is a demo store. You can place a demo order, and no money is collected. Current shipping is free."
            )
            return Response({"answer": answer})

        contact_question = any(term in query for term in (
            "contact", "email", "phone", "call", "تواصل", "البريد", "ايميل", "إيميل", "رقم الجوال", "رقم الهاتف",
        ))
        if contact_question:
            answer = (
                "تقدر تتواصل معنا على الرقم +966 50 123 4567 أو البريد Naif7iqul@gmail.com."
                if language == "ar"
                else "You can contact us at +966 50 123 4567 or Naif7iqul@gmail.com."
            )
            return Response({"answer": answer})

        categories = (
            (("rose", "floral", "ورد", "زهري"), ("rose", "floral", "ورد", "زهري")),
            (("musk", "clean", "daily", "مسك", "يومي", "نظيف"), ("musk", "clean", "daily", "مسك", "يومي", "نظيف")),
            (("oud", "amber", "warm", "evening", "عود", "عنبر", "مساء", "دافئ"), ("oud", "amber", "warm", "evening", "عود", "عنبر", "مساء", "دافئ")),
            (("citrus", "fresh", "bergamot", "حمضيات", "منعش", "برغموت"), ("citrus", "fresh", "bergamot", "حمضيات", "منعش", "برغموت")),
        )
        matched = []
        for query_terms, product_terms in categories:
            if any(term in query for term in query_terms):
                matched = [
                    product for product in products
                    if any(term in f"{product.name} {product.name_en} {product.description} {product.description_en}".casefold() for term in product_terms)
                ]
                break

        if matched:
            recommendation = matched[:3]
            answer = (
                f"أقترح عليك هذه العطور من مجموعتنا:\n{details(recommendation)}"
                if language == "ar"
                else f"These perfumes may suit you:\n{details(recommendation)}"
            )
            return Response({"answer": answer})

        catalog_question = any(term in query for term in (
            "perfume", "perfumes", "products", "collection", "recommend", "suggest", "عطر", "عطور", "منتج", "منتجات", "المجموعة",
        ))
        if catalog_question:
            answer = (
                f"هذه العطور المتوفرة في مجموعتنا:\n{details(products)}"
                if language == "ar"
                else f"Here are the perfumes in our collection:\n{details(products)}"
            )
            return Response({"answer": answer})

        about_question = any(term in query for term in (
            "about the store", "what is this site", "about perfume", "عن المتجر", "عن الموقع", "ايش يقدم", "ماذا يقدم",
        ))
        if about_question:
            answer = (
                "هذا متجر عطور تجريبي يعرض عطوراً ومعلوماتها ويسمح بإرسال طلب تجريبي بدون تحصيل أموال."
                if language == "ar"
                else "This is a demo perfume store. It shows perfume details and lets you place a demo order without collecting money."
            )
            return Response({"answer": answer})

        product = next(
            (item for item in products if item.name.casefold() in query or (item.name_en and item.name_en.casefold() in query)),
            None,
        )
        if product:
            description = product.description if language == "ar" else (product.description_en or product.description)
            answer = (
                f"{product_name(product)}: {description} السعر: SAR {product.price:.2f}."
                if language == "ar"
                else f"{product_name(product)}: {description} Price: SAR {product.price:.2f}."
            )
            return Response({"answer": answer})

        answer = (
            "أقدر أساعدك في اختيار عطر، معرفة الأسعار، ومعلومات الطلب التجريبي. اسألني عن المسك أو العود أو الورد أو الحمضيات."
            if language == "ar"
            else "I can help you choose a perfume, check prices, or explain demo orders. Ask me about musk, oud, rose, or citrus."
        )
        return Response({"answer": answer})
