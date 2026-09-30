from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, Order, OrderItem, Product, StoreContent


admin.site.site_header = 'PERFUME | إدارة المتجر'
admin.site.site_title = 'إدارة PERFUME'
admin.site.index_title = 'إدارة منتجات وطلبات المتجر'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'name_en', 'price', 'stock', 'available', 'created_at')
    list_filter = ('available',)
    search_fields = ('name', 'name_en', 'description', 'description_en')
    list_editable = ('stock', 'available')
    list_per_page = 20
    readonly_fields = ('image_preview', 'created_at')
    fields = ('name', 'name_en', 'description', 'description_en', 'price', 'image', 'image_preview', 'stock', 'available', 'created_at')

    @admin.display(description='معاينة الصورة')
    def image_preview(self, obj):
        if not obj or not obj.image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width:64px;height:64px;object-fit:cover;border-radius:10px" />',
            obj.image.url,
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'total', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('id', 'full_name', 'phone', 'user__username', 'user__email')
    readonly_fields = ('user', 'subtotal', 'shipping_fee', 'total', 'payment_status', 'created_at')
    inlines = (OrderItemInline,)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ('product',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('updated_at',)
    inlines = (CartItemInline,)


@admin.register(StoreContent)
class StoreContentAdmin(admin.ModelAdmin):
    list_display = ('id',)
    fieldsets = (
        ('نصوص الصفحة الرئيسية', {'fields': ('hero_title_ar', 'hero_title_en', 'hero_description_ar', 'hero_description_en')}),
        ('قسم قصتنا', {'fields': ('story_title_ar', 'story_title_en', 'story_description_ar', 'story_description_en')}),
    )
