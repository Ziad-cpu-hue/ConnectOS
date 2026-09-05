from django.db import migrations


class Migration(migrations.Migration):
    """
    حجب المواقع الإباحية بقى إعداد أساسي إجباري على مستوى المنصة كلها (يتفرض
    تلقائيًا من سكريبت تركيب كل جهاز ميكروتيك)، مش خيار اختياري لكل باقة.
    عشان كده اتشال الحقل ده نهائيًا من هنا — مفيش أي مكان في النظام تقدر
    بيه توقف الحجب ده.
    """

    dependencies = [
        ("plans", "0002_plan_allow_open_speed_plan_block_adult_sites_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="plan",
            name="block_adult_sites",
        ),
    ]
