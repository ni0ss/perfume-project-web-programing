"""Send read-only public product queries to the optional PostgreSQL replica."""

from django.conf import settings


class ProductReadReplicaRouter:
    """Use the replica for product reads while keeping writes on the primary.

    Replication is asynchronous, so this router is limited to catalog products.
    Authentication, sessions, carts, checkout, and administration always use
    the primary database to avoid stale reads in user-facing workflows.
    """

    def db_for_read(self, model, **hints):
        if (
            model._meta.app_label == "store"
            and model._meta.model_name == "product"
            and "replica" in settings.DATABASES
        ):
            return "replica"
        return None

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "replica":
            return False
        return None
