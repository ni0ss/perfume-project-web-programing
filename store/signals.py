from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product


PUBLIC_CATALOG_VERSION_KEY = "store:public-catalog-version:v1"


def _bump_public_catalog_version():
    try:
        cache.incr(PUBLIC_CATALOG_VERSION_KEY)
    except ValueError:
        # The version key is not present on a fresh cache or after a cache
        # restart. Setting it also makes subsequent invalidations atomic.
        cache.set(PUBLIC_CATALOG_VERSION_KEY, 1, timeout=None)


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_public_catalog_cache(**kwargs):
    _bump_public_catalog_version()
