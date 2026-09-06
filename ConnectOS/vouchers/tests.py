from django.test import TestCase

from core.models import Company
from plans.models import Plan
from vouchers.models import VoucherBatch


class VoucherGenerationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="شركة تجربة")
        self.plan = Plan.objects.create(company=self.company, name="باقة", duration_days=1, price=5)

    def test_generate_vouchers_creates_correct_quantity(self):
        batch = VoucherBatch.objects.create(company=self.company, plan=self.plan, quantity=50)
        batch.generate_vouchers()
        self.assertEqual(batch.vouchers.count(), 50)

    def test_generated_codes_are_unique(self):
        batch = VoucherBatch.objects.create(company=self.company, plan=self.plan, quantity=100)
        batch.generate_vouchers()
        codes = list(batch.vouchers.values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)), "كل الأكواد لازم تكون فريدة، مفيش تكرار")

    def test_voucher_activate_sets_expiry_from_plan_duration(self):
        batch = VoucherBatch.objects.create(company=self.company, plan=self.plan, quantity=1)
        batch.generate_vouchers()
        voucher = batch.vouchers.first()
        self.assertEqual(voucher.status, "unused")
        voucher.activate()
        self.assertEqual(voucher.status, "active")
        self.assertIsNotNone(voucher.expires_at)
