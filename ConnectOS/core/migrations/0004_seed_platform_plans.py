from django.db import migrations

# باقات ConnectOS — نفس فكرة باقات Smart Radius بس بقيمة أعلى وسعر أقل
# (عدد مشتركين/سيرفرات/كروت أكتر، وتكلفة شهرية أقل من المنافس على كل مستوى)
PLANS = [
    # name,                 max_clients, max_servers, max_print_cards, price, featured, order
    ("المبتدئين",           150,   2,   2000,    70,   False, 1),
    ("البداية",             300,   4,   4000,    120,  False, 2),
    ("الانطلاق",            500,   6,   5500,    220,  False, 3),
    ("النمو",               700,   7,   7500,    280,  True,  4),
    ("التوسع",              1000,  8,   9000,    340,  False, 5),
    ("الاحتراف",            1500,  9,   10000,   430,  False, 6),
    ("المتقدمة",            2000,  10,  13000,   500,  False, 7),
    ("الأعمال",             3000,  13,  16000,   800,  False, 8),
    ("المؤسسات",            4000,  14,  19000,   1500, False, 9),
    ("الشبكات الكبرى",      5000,  50,  20000,   2400, False, 10),
    ("عملاق الشبكات",       5500,  90,  24000,   4000, False, 11),
    ("VIP للشبكات",         6000,  90,  45000,   5000, False, 12),
]


def seed_plans(apps, schema_editor):
    PlatformPlan = apps.get_model("core", "PlatformPlan")
    for name, max_clients, max_servers, max_print_cards, price, featured, order in PLANS:
        PlatformPlan.objects.update_or_create(
            name=name,
            defaults=dict(
                max_clients=max_clients,
                max_servers=max_servers,
                max_print_cards=max_print_cards,
                price_monthly=price,
                is_featured=featured,
                order=order,
                is_active=True,
            ),
        )


def remove_plans(apps, schema_editor):
    PlatformPlan = apps.get_model("core", "PlatformPlan")
    PlatformPlan.objects.filter(name__in=[p[0] for p in PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_platformplan_platformpayment_confirmed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
