from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import Cart, CartItem, Product


class RegistrationAndAccountTests(TestCase):
    def test_registration_creates_user_and_delivery_profile(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-shopper",
                "email": "shopper@example.com",
                "full_name": "New Shopper",
                "phone": "+966500000001",
                "city": "Riyadh",
                "address": "Test Street 1",
                "password1": "Safe-Test-Pass-941!",
                "password2": "Safe-Test-Pass-941!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="new-shopper")
        self.assertEqual(user.email, "shopper@example.com")
        self.assertEqual(user.customer_profile.full_name, "New Shopper")
        self.assertEqual(user.customer_profile.city, "Riyadh")

    def test_profile_requires_login_and_shows_only_signed_in_shopper(self):
        user_model = get_user_model()
        shopper = user_model.objects.create_user(
            username="shopper", password="Safe-Test-Pass-941!", email="shopper@example.com"
        )

        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

        self.client.force_login(shopper)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "shopper@example.com")

    def test_login_merges_anonymous_cart_and_caps_quantity_at_stock(self):
        user_model = get_user_model()
        shopper = user_model.objects.create_user(
            username="shopper", password="Safe-Test-Pass-941!"
        )
        product = Product.objects.create(
            name="عطر تجريبي",
            description="وصف تجريبي",
            price="90.00",
            stock=2,
        )
        session = self.client.session
        session["perfume_cart"] = {str(product.pk): 8}
        session.save()

        response = self.client.post(
            reverse("login"),
            {"username": shopper.username, "password": "Safe-Test-Pass-941!"},
        )

        self.assertEqual(response.status_code, 302)
        item = CartItem.objects.get(cart__user=shopper, product=product)
        self.assertEqual(item.quantity, 2)
        self.assertNotIn("perfume_cart", self.client.session)
        self.assertTrue(Cart.objects.filter(user=shopper).exists())
