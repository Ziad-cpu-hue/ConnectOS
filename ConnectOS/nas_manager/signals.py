from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from radius_core.models import RadNas

from .models import NASServer


@receiver(post_save, sender=NASServer)
def sync_nas_to_radius(sender, instance, **kwargs):
    """أي جهاز يتضاف/يتعدل في nas_manager بينعكس فورًا على جدول nas
    الحقيقي بتاع FreeRADIUS، عشان الجهاز يبقى NAS client معروف ومسموح له."""
    RadNas.objects.update_or_create(
        nasname=instance.ip_address,
        defaults={
            "shortname": instance.name[:32],
            "type": "mikrotik",
            "secret": instance.secret,
            "description": f"{instance.company.name} — {instance.region}",
        },
    )


@receiver(post_delete, sender=NASServer)
def remove_nas_from_radius(sender, instance, **kwargs):
    RadNas.objects.filter(nasname=instance.ip_address).delete()
