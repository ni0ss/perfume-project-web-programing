from django.core.management.base import BaseCommand

from store.models import Product


DEMO_PRODUCTS = (
    {
        "name": "الورد الجوري",
        "name_en": "Rose Musk",
        "description": "نفحات الورد الجوري الناعمة تمتزج بلمسات من المسك لترك أثر أنيق وخفيف.",
        "description_en": "Soft rose notes blend with musk for a light, elegant scent.",
        "price": "420.00",
        "image": "products/perfume-rose.jpg",
        "available": True,
        "stock": 9,
    },
    {
        "name": "عنبر الليل",
        "name_en": "Night Amber",
        "description": "عطر شرقي دافئ بنفحات العنبر والعود، بلمسات خشبية أنيقة للمساء والمناسبات.",
        "description_en": "Warm amber and oud meet soft wood notes for evenings and special occasions.",
        "price": "590.00",
        "image": "products/perfume-amber.jpg",
        "available": True,
        "stock": 4,
    },
    {
        "name": "مسك أبيض",
        "name_en": "White Musk",
        "description": "نفحات مسك ناعمة ونظيفة مع لمسات زهرية خفيفة، مناسب للاستخدام اليومي.",
        "description_en": "Clean, soft musk with light floral notes for everyday use.",
        "price": "320.00",
        "image": "products/perfume-musk.jpg",
        "available": True,
        "stock": 12,
    },
    {
        "name": "عود المساء",
        "name_en": "Evening Oud",
        "description": "تركيبة شرقية عميقة تجمع خشب العود مع العنبر والتوابل الدافئة.",
        "description_en": "A rich scent with oud wood, amber, and warm spices.",
        "price": "680.00",
        "image": "products/perfume-oud.jpg",
        "available": True,
        "stock": 5,
    },
    {
        "name": "نسيم الحمضيات",
        "name_en": "Citrus Breeze",
        "description": "نفحات برغموت وحمضيات منعشة مع قاعدة خشبية خفيفة لبداية يوم حيوية.",
        "description_en": "Fresh bergamot and citrus with a light wood base for a bright start to the day.",
        "price": "340.00",
        "image": "products/perfume-citrus.jpg",
        "available": True,
        "stock": 8,
    },
)


class Command(BaseCommand):
    help = "Create the public demo perfume catalog if products are missing."

    def handle(self, *args, **options):
        created = 0
        for product in DEMO_PRODUCTS:
            _, was_created = Product.objects.get_or_create(
                name=product["name"], defaults=product
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo catalog ready: {len(DEMO_PRODUCTS)} products ({created} created)."
            )
        )
