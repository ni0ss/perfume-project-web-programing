from django.db.models import Sum

from .models import Cart
from .views import CART_SESSION_KEY


def cart_summary(request):
    if request.user.is_authenticated:
        quantity = Cart.objects.filter(user=request.user).aggregate(
            quantity=Sum('items__quantity'),
        )['quantity'] or 0
    else:
        session_cart = request.session.get(CART_SESSION_KEY, {})
        quantity = sum(
            max(0, int(value))
            for value in session_cart.values()
            if str(value).isdigit()
        ) if isinstance(session_cart, dict) else 0
    return {'cart_item_count': quantity}
