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
from .assistant_service import answer_store_question


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
    """Classify a store question locally and answer from the live catalogue."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request):
        raw_message = request.data.get("message", "")
        if not isinstance(raw_message, str):
            return Response({"error": "Please enter a text question."}, status=400)
        message = raw_message.strip()
        if not message:
            return Response({"error": "Please enter a question."}, status=400)
        if len(message) > 500:
            return Response({"error": "Please keep your question under 500 characters."}, status=400)

        products = Product.objects.filter(available=True, stock__gt=0).order_by("price", "name")
        return Response(answer_store_question(message, request.data.get("language"), products))
