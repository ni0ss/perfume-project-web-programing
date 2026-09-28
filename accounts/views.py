from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import RegisterForm
from store.models import Cart, CartItem, Product
from store.views import CART_SESSION_KEY


class StoreLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        if self.request.user.is_staff:
            return reverse('admin_dashboard')
        return super().get_success_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        session_cart = self.request.session.get(CART_SESSION_KEY, {})
        if isinstance(session_cart, dict) and session_cart:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
            for product in Product.objects.filter(
                pk__in=session_cart.keys(),
                available=True,
                stock__gt=0,
            ):
                try:
                    quantity = max(1, int(session_cart.get(str(product.pk), session_cart.get(product.pk, 1))))
                except (TypeError, ValueError):
                    continue
                item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': min(quantity, product.stock)},
                )
                if not created:
                    item.quantity = min(item.quantity + quantity, product.stock)
                    item.save(update_fields=('quantity',))
            self.request.session.pop(CART_SESSION_KEY, None)
        return response


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {
        'form': form
    })


@login_required
def profile(request):
    orders = request.user.orders.prefetch_related('items')
    return render(request, 'accounts/profile.html', {'orders': orders})
# Create your views here.
