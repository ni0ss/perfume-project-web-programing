from django.conf import settings
from django.db import models
from django.utils.translation import get_language


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='الاسم بالعربية')
    name_en = models.CharField(max_length=200, blank=True, default='', verbose_name='Name in English')
    description = models.TextField(verbose_name='الوصف بالعربية')
    description_en = models.TextField(blank=True, default='', verbose_name='Description in English')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    available = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=10, verbose_name='الكمية المتوفرة')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def localized_name(self):
        if get_language() == 'en' and self.name_en:
            return self.name_en
        return self.name

    @property
    def localized_description(self):
        if get_language() == 'en' and self.description_en:
            return self.description_en
        return self.description

    def __str__(self):
        return self.name


class StoreContent(models.Model):
    """Editable bilingual copy for the home page, managed from the store dashboard."""

    hero_title_ar = models.CharField(max_length=180, default='عطرك يروي قصتك.', verbose_name='عنوان الواجهة بالعربية')
    hero_title_en = models.CharField(max_length=180, default='Your scent. Your signature.', verbose_name='Hero title in English')
    hero_description_ar = models.TextField(default='اكتشف مجموعة مختارة من العطور الراقية التي تجمع بين الأناقة والأصالة والحضور المميز.', verbose_name='وصف الواجهة بالعربية')
    hero_description_en = models.TextField(default='Discover refined fragrances selected for elegance, character and an unforgettable presence.', verbose_name='Hero description in English')
    story_title_ar = models.CharField(max_length=180, default='الأناقة تبدأ بالتفاصيل.', verbose_name='عنوان القصة بالعربية')
    story_title_en = models.CharField(max_length=180, default='Luxury lives in the details.', verbose_name='Story title in English')
    story_description_ar = models.TextField(default='بنينا PERFUME ليكون تجربة تسوق بسيطة وحديثة لعشاق العطور. نركز على جودة العرض، سهولة الاستخدام، وتنظيم المنتجات بطريقة واضحة.', verbose_name='وصف القصة بالعربية')
    story_description_en = models.TextField(default='PERFUME is designed as a clean, modern shopping experience for fragrance lovers, focused on presentation, usability and carefully organized products.', verbose_name='Story description in English')

    @classmethod
    def get_solo(cls):
        content, _ = cls.objects.get_or_create(pk=1)
        return content

    def __str__(self):
        return 'PERFUME home page content'


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart for {self.user}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('cart', 'product'), name='unique_product_per_cart'),
        ]

    def __str__(self):
        return f'{self.quantity} × {self.product.name}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'جديد'
        PROCESSING = 'processing', 'قيد التجهيز'
        SHIPPED = 'shipped', 'تم الشحن'
        DELIVERED = 'delivered', 'مكتمل'
        CANCELLED = 'cancelled', 'ملغي'

    class PaymentStatus(models.TextChoices):
        DEMO = 'demo', 'دفع تجريبي'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.DEMO,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Order #{self.pk} — {self.user}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.quantity} × {self.product_name}'
