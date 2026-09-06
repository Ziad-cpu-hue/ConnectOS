from django.test import TestCase

from core.models import Company
from debts.models import DebtTransaction, Reseller


class DebtCalculationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="شركة تجربة")
        self.reseller = Reseller.objects.create(
            company=self.company, name="موزع تجربة", phone="0100", debt_limit=500,
        )

    def test_debt_starts_at_zero(self):
        self.assertEqual(self.reseller.current_debt, 0)

    def test_card_delivery_increases_debt(self):
        DebtTransaction.objects.create(reseller=self.reseller, type="card_delivery", amount=300)
        self.assertEqual(self.reseller.current_debt, 300)

    def test_payment_decreases_debt(self):
        DebtTransaction.objects.create(reseller=self.reseller, type="card_delivery", amount=300)
        DebtTransaction.objects.create(reseller=self.reseller, type="payment", amount=120)
        self.assertEqual(self.reseller.current_debt, 180)

    def test_over_limit_flag_true_when_exceeding(self):
        DebtTransaction.objects.create(reseller=self.reseller, type="card_delivery", amount=600)
        self.assertTrue(self.reseller.is_over_limit)

    def test_over_limit_flag_false_when_under(self):
        DebtTransaction.objects.create(reseller=self.reseller, type="card_delivery", amount=200)
        self.assertFalse(self.reseller.is_over_limit)

    def test_zero_limit_means_never_over(self):
        self.reseller.debt_limit = 0
        self.reseller.save()
        DebtTransaction.objects.create(reseller=self.reseller, type="card_delivery", amount=99999)
        self.assertFalse(self.reseller.is_over_limit)
