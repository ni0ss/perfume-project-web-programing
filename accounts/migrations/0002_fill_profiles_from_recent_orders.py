from django.db import migrations


def fill_profiles_from_recent_orders(apps, schema_editor):
    CustomerProfile = apps.get_model('accounts', 'CustomerProfile')
    Order = apps.get_model('store', 'Order')
    seen_user_ids = set()

    recent_orders = Order.objects.order_by('user_id', '-created_at', '-pk').iterator()
    for order in recent_orders:
        if order.user_id in seen_user_ids:
            continue
        seen_user_ids.add(order.user_id)

        details = {
            'full_name': order.full_name,
            'phone': order.phone,
            'city': order.city,
            'address': order.address,
        }
        profile, created = CustomerProfile.objects.get_or_create(
            user_id=order.user_id,
            defaults=details,
        )
        if not created and not any((profile.full_name, profile.phone, profile.city, profile.address)):
            for field, value in details.items():
                setattr(profile, field, value)
            profile.save(update_fields=(*details.keys(), 'updated_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('store', '0003_storecontent_product_description_en_product_name_en_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_profiles_from_recent_orders, migrations.RunPython.noop),
    ]
