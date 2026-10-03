from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import CustomerProfile
from .forms import CheckoutForm
from .models import Cart, CartItem, Order, OrderItem, Product, StoreContent


CART_SESSION_KEY = 'perfume_cart'
SHIPPING_FEE = Decimal('0.00')


def _localized_message(request, arabic, english):
    return arabic if request.LANGUAGE_CODE == 'ar' else english


def home(request):
    products = Product.objects.filter(available=True).order_by('-created_at')
    return render(request, 'store/home.html', {
        'products': products,
        'page_content': StoreContent.get_solo(),
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, _localized_message(request, 'هذه الصفحة مخصصة لإدارة المتجر.', 'This page is for store staff only.'))
        return redirect('home')
    orders = Order.objects.select_related('user')
    products = Product.objects.all()
    low_stock_products = products.filter(available=True, stock__lte=5).order_by('stock', 'name')
    return render(request, 'store/admin_dashboard.html', {
        'product_count': products.count(),
        'available_product_count': products.filter(available=True, stock__gt=0).count(),
        'low_stock_count': low_stock_products.count(),
        'order_count': orders.count(),
        'pending_order_count': orders.filter(status=Order.Status.PENDING).count(),
        'demo_order_value': orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00'),
        'recent_orders': orders,
        'low_stock_products': low_stock_products[:6],
        'manage_products': products.order_by('-created_at'),
        'page_content': StoreContent.get_solo(),
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, available=True)
    return render(request, 'store/product_detail.html', {'product': product})


def _session_cart(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    return cart if isinstance(cart, dict) else {}


def _cart_lines(request):
    """Return normalized cart rows for both anonymous and signed-in shoppers."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return [
            {
                'product': item.product,
                'quantity': item.quantity,
                'line_total': item.product.price * item.quantity,
                'available_quantity': item.product.stock,
                'in_stock': item.product.available and item.product.stock >= item.quantity,
            }
            for item in cart.items.select_related('product').order_by('id')
        ]

    session_cart = _session_cart(request)
    products = Product.objects.filter(pk__in=session_cart.keys())
    by_id = {str(product.pk): product for product in products}
    lines = []
    for product_id, raw_quantity in session_cart.items():
        product = by_id.get(str(product_id))
        if not product:
            continue
        try:
            quantity = max(1, int(raw_quantity))
        except (TypeError, ValueError):
            continue
        lines.append({
            'product': product,
            'quantity': quantity,
            'line_total': product.price * quantity,
            'available_quantity': product.stock,
            'in_stock': product.available and product.stock >= quantity,
        })
    return lines


def _cart_totals(lines):
    subtotal = sum((line['line_total'] for line in lines), Decimal('0.00'))
    return subtotal, SHIPPING_FEE, subtotal + SHIPPING_FEE


def cart_detail(request):
    lines = _cart_lines(request)
    subtotal, shipping_fee, total = _cart_totals(lines)
    return render(request, 'store/cart.html', {
        'cart_lines': lines,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': total,
        'can_checkout': bool(lines) and all(line['in_stock'] for line in lines),
    })


def cart_add(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, pk=product_id, available=True)
    if product.stock < 1:
        error_message = _localized_message(request, 'هذا المنتج غير متوفر حالياً.', 'This product is currently unavailable.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('home')

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            item.quantity = min(item.quantity + 1, product.stock)
            item.save(update_fields=('quantity',))
    else:
        cart = _session_cart(request)
        key = str(product.pk)
        cart[key] = min(int(cart.get(key, 0)) + 1, product.stock)
        request.session[CART_SESSION_KEY] = cart
        request.session.modified = True

    success_message = _localized_message(request, 'تمت إضافة المنتج إلى السلة.', 'Product added to your cart.')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.is_authenticated:
            cart_item_count = CartItem.objects.filter(cart__user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
        else:
            cart_item_count = sum(int(quantity) for quantity in _session_cart(request).values())
        return JsonResponse({
            'ok': True,
            'message': success_message,
            'cart_item_count': cart_item_count,
        })

    messages.success(request, success_message)
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('home')


def cart_update(request, product_id):
    if request.method != 'POST':
        return redirect('cart')
    product = get_object_or_404(Product, pk=product_id)
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        quantity = 1

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        item = CartItem.objects.filter(cart=cart, product=product).first() if cart else None
        if item:
            if quantity <= 0 or product.stock <= 0 or not product.available:
                item.delete()
            else:
                item.quantity = min(quantity, product.stock)
                item.save(update_fields=('quantity',))
    else:
        cart = _session_cart(request)
        key = str(product.pk)
        if key in cart:
            if quantity <= 0 or product.stock <= 0 or not product.available:
                cart.pop(key, None)
            else:
                cart[key] = min(quantity, product.stock)
            request.session[CART_SESSION_KEY] = cart
            request.session.modified = True
    return redirect('cart')


def cart_remove(request, product_id):
    if request.method != 'POST':
        return redirect('cart')
    if request.user.is_authenticated:
        CartItem.objects.filter(
            cart__user=request.user,
            product_id=product_id,
        ).delete()
    else:
        cart = _session_cart(request)
        cart.pop(str(product_id), None)
        request.session[CART_SESSION_KEY] = cart
        request.session.modified = True
    return redirect('cart')


@login_required
def checkout(request):
    lines = _cart_lines(request)
    if not lines:
        messages.info(request, _localized_message(request, 'أضف منتجاً إلى السلة قبل إتمام الطلب.', 'Add an item to your cart before checkout.'))
        return redirect('cart')

    subtotal, shipping_fee, total = _cart_totals(lines)
    delivery_profile = getattr(request.user, 'customer_profile', None)
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    locked_items = []
                    for line in lines:
                        product = Product.objects.select_for_update().get(pk=line['product'].pk)
                        if not product.available or product.stock < line['quantity']:
                            raise ValueError(product.name)
                        locked_items.append((product, line['quantity']))

                    subtotal = sum(
                        (product.price * quantity for product, quantity in locked_items),
                        Decimal('0.00'),
                    )
                    order = form.save(commit=False)
                    order.user = request.user
                    order.subtotal = subtotal
                    order.shipping_fee = shipping_fee
                    order.total = subtotal + shipping_fee
                    order.save()

                    for product, quantity in locked_items:
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            product_name=product.localized_name,
                            unit_price=product.price,
                            quantity=quantity,
                        )
                        product.stock -= quantity
                        product.save(update_fields=('stock',))

                    Cart.objects.filter(user=request.user).delete()
                    request.session.pop(CART_SESSION_KEY, None)
            except (Product.DoesNotExist, ValueError):
                messages.error(request, _localized_message(request, 'تغير توفر أحد المنتجات. راجع السلة ثم حاول مجدداً.', 'An item’s availability changed. Review your cart and try again.'))
                return redirect('cart')

            CustomerProfile.objects.update_or_create(
                user=request.user,
                defaults={
                    'full_name': form.cleaned_data['full_name'],
                    'phone': form.cleaned_data['phone'],
                    'city': form.cleaned_data['city'],
                    'address': form.cleaned_data['address'],
                },
            )

            messages.success(request, _localized_message(request, 'تم تسجيل طلبك التجريبي بنجاح، ولم يتم تحصيل أي مبلغ.', 'Your demo order was placed. No payment was collected.'))
            return redirect('order_confirmation', order_id=order.pk)
    else:
        profile = delivery_profile
        form = CheckoutForm(initial={
            'full_name': (profile.full_name if profile and profile.full_name else request.user.get_full_name()),
            'phone': profile.phone if profile else '',
            'city': profile.city if profile else '',
            'address': profile.address if profile else '',
        })

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_lines': lines,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': total,
        'has_saved_delivery_details': bool(
            delivery_profile
            and delivery_profile.full_name
            and delivery_profile.phone
            and delivery_profile.city
            and delivery_profile.address
        ),
    })


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=order_id,
        user=request.user,
    )
    return render(request, 'store/order_confirmation.html', {'order': order})
