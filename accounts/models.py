from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    """Saved delivery details used to prefill a customer's future orders."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile',
    )
    full_name = models.CharField(max_length=160, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Delivery details for {self.user}'
