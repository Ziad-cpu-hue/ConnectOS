import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Company, PlatformPayment, User
from debts.models import DebtTransaction, Reseller
from nas_manager.models import NASServer
from plans.models import Plan
from vouchers.models import Voucher, VoucherBatch, VoucherTemplate


class Command(BaseCommand):
    help = "يولّد بيانات تجريبية كاملة لتجربة ConnectOS مباشرة"

    def handle(self, *args, **options):
        self.stdout.write("جاري إنشاء البيانات التجريبية...")

        company, _ = Company.objects.get_or_create(
            name="شبكة النور نت",
            defaults=dict(owner_phone="01128839569", subscription_plan="growth",
                          monthly_fee=Decimal("450.00")),
        )

        PlatformPayment.objects.get_or_create(company=company, amount=Decimal("450.00"), method="تحويل بنكي")

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", email="admin@connectos.local", password="admin12345",
                company=company, role="platform_admin", phone="01000000000",
            )
            self.stdout.write(self.style.SUCCESS("تم إنشاء المستخدم: admin / admin12345 (مدير المنصة)"))

        if not User.objects.filter(username="owner").exists():
            User.objects.create_user(
                username="owner", email="owner@connectos.local", password="owner12345",
                company=company, role="owner", first_name="محمد", last_name="عبدالله", phone="01128839569",
            )
            self.stdout.write(self.style.SUCCESS("تم إنشاء المستخدم: owner / owner12345 (صاحب الشبكة)"))

        regions = ["حي المعادي", "شارع الجمهورية", "حي فيصل", "مدينة نصر", "العجوزة"]
        for i, region in enumerate(regions, start=1):
            NASServer.objects.get_or_create(
                company=company, name=f"عمود {region}",
                defaults=dict(
                    ip_address=f"10.10.{i}.1", secret=f"secret-{i}", region=region,
                    is_online=random.choice([True, True, True, False]),
                    last_seen=timezone.now(),
                ),
            )

        plans_data = [
            ("باقة 500 ميجا - يوم واحد", 500, 1, 5),
            ("باقة 1700 ميجا - 3 أيام", 1700, 3, 10),
            ("باقة 6000 ميجا - أسبوع", 6000, 7, 25),
            ("باقة غير محدودة - شهر", None, 30, 90),
        ]
        plans = []
        for name, quota, days, price in plans_data:
            plan, _ = Plan.objects.get_or_create(
                company=company, name=name,
                defaults=dict(quota_mb=quota, duration_days=days, price=Decimal(price)),
            )
            plans.append(plan)

        template, _ = VoucherTemplate.objects.get_or_create(
            company=company, name="القالب الكلاسيكي",
            defaults=dict(primary_color="#1BA89B", secondary_color="#E7A83D",
                          logo_text="5G.NET", support_phone="01128839569", is_default=True),
        )

        if not VoucherBatch.objects.filter(company=company).exists():
            for plan in plans[:2]:
                batch = VoucherBatch.objects.create(company=company, plan=plan, template=template, quantity=20)
                batch.generate_vouchers()
                # فعّل بعض الكروت عشوائيًا عشان الإحصائيات تبان
                for v in batch.vouchers.order_by("?")[:6]:
                    v.activate()

        resellers_data = [
            ("سوبر ماركت البركة", "01011122233", "شارع الجمهورية", 300),
            ("محل التوفيقية", "01022233344", "حي المعادي", 200),
            ("سوبر ماركت الأمل", "01033344455", "مدينة نصر", 150),
        ]
        for name, phone, location, limit in resellers_data:
            reseller, created = Reseller.objects.get_or_create(
                company=company, name=name,
                defaults=dict(phone=phone, location=location, debt_limit=Decimal(limit)),
            )
            if created:
                batch = VoucherBatch.objects.filter(company=company).first()
                if batch:
                    amount = batch.plan.price * 10
                    DebtTransaction.objects.create(
                        reseller=reseller, type="card_delivery", amount=amount,
                        voucher_batch=batch, note="تسليم أولي",
                    )
                    if random.choice([True, False]):
                        DebtTransaction.objects.create(
                            reseller=reseller, type="payment",
                            amount=amount / 2, payment_method="cash", note="سداد جزئي",
                        )

        self.stdout.write(self.style.SUCCESS("تم تجهيز البيانات التجريبية بنجاح."))
