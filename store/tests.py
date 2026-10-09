from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .assistant_ml import classify_intent, normalize_text, tokenize
from .models import Product, StoreContent


class LocalIntentClassifierTests(TestCase):
    def test_normalizes_arabic_variants_and_combined_prefixes(self):
        self.assertEqual(normalize_text("إلى الورد"), "الي الورد")
        tokens = tokenize("وبالعطر للزائر")
        self.assertIn("عطر", tokens)
        self.assertIn("زاير", tokens)

    def test_classifies_store_questions_in_both_languages(self):
        examples = (
            ("هل عندكم مسك أبيض؟", "catalog"),
            ("What is the price of White Musk?", "price"),
            ("أميل إلى العود، رشح لي عطرًا", "recommendation"),
            ("How do I contact the store?", "contact"),
            ("كيف أطلب عطرًا للتوصيل؟", "delivery_order"),
            ("What does this shop offer?", "store_info"),
            ("ما حالة الطقس اليوم؟", "other"),
        )
        for message, expected in examples:
            with self.subTest(message=message):
                self.assertEqual(classify_intent(message)[0], expected)

    def test_product_ranking_uses_bilingual_scent_profiles(self):
        rose = Product.objects.create(
            name="عطر الورد",
            name_en="Rose Perfume",
            description="نفحات وردية ناعمة",
            description_en="Soft floral rose notes",
            price=Decimal("100.00"),
            available=True,
            stock=4,
        )
        citrus = Product.objects.create(
            name="عطر الحمضيات",
            name_en="Citrus Perfume",
            description="رائحة منعشة",
            description_en="A fresh citrus fragrance",
            price=Decimal("90.00"),
            available=True,
            stock=4,
        )
        client = APIClient()
        response = client.post(
            "/api/assistant/",
            {"message": "Recommend a soft rose scent", "language": "en"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(rose.name_en, response.data["answer"])
        self.assertNotIn(citrus.name_en, response.data["answer"])


class LocalAssistantAPITests(TestCase):
    def setUp(self):
        Product.objects.create(
            name="مسك أبيض",
            name_en="White Musk",
            description="عطر ناعم",
            description_en="A soft fragrance",
            price=Decimal("150.00"),
            available=True,
            stock=5,
        )
        self.client = APIClient()

    def test_assistant_is_public_and_uses_requested_language(self):
        response = self.client.post(
            "/api/assistant/",
            {"message": "What is the price of White Musk?", "language": "en"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("White Musk", response.data["answer"])
        self.assertEqual(response.data["intent"], "price")
        self.assertEqual(response.data["classifier"], "local-hybrid-nb-2.1")

    def test_assistant_rejects_empty_non_text_and_oversized_input(self):
        for payload in ({"message": "   "}, {"message": 42}, {"message": "x" * 501}):
            with self.subTest(payload_type=type(payload["message"]).__name__):
                response = self.client.post("/api/assistant/", payload, format="json")
                self.assertEqual(response.status_code, 400)


class StoreAPIPermissionTests(TestCase):
    def setUp(self):
        Product.objects.create(
            name="عنبر الليل",
            name_en="Night Amber",
            description="عطر دافئ",
            description_en="A warm fragrance",
            price=Decimal("220.00"),
            available=True,
            stock=3,
        )
        self.client = APIClient()

    def test_products_are_publicly_readable_but_not_writable(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        denied = self.client.post(
            "/api/products/",
            {"name": "Test", "description": "Test", "price": "5.00"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_only_staff_can_create_products_and_edit_store_content(self):
        User = get_user_model()
        regular_user = User.objects.create_user(username="shopper", password="safe-password-1")
        self.client.force_authenticate(user=regular_user)
        denied = self.client.patch(
            "/api/site-content/",
            {"hero_title_en": "Changed"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        staff_user = User.objects.create_user(
            username="manager", password="safe-password-2", is_staff=True
        )
        self.client.force_authenticate(user=staff_user)
        updated = self.client.patch(
            "/api/site-content/",
            {"hero_title_en": "A New Scent Story"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(StoreContent.objects.get(pk=1).hero_title_en, "A New Scent Story")

        created = self.client.post(
            "/api/products/",
            {
                "name": "ورد المساء",
                "name_en": "Evening Rose",
                "description": "ورد ناعم",
                "description_en": "Soft rose notes",
                "price": "125.00",
                "stock": 5,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(Product.objects.filter(name_en="Evening Rose").exists())
