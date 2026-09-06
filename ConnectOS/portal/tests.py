from django.test import TestCase
from django.urls import reverse

from core.models import Company
from plans.models import Plan
from subscribers.models import Subscriber


class PortalAuthTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="شركة تجربة")
        self.plan = Plan.objects.create(company=self.company, name="باقة", duration_days=30, price=50)
        self.sub = Subscriber.objects.create(
            company=self.company, full_name="عميل تجربة", username="client1",
            password="clientpass", plan=self.plan,
        )

    def test_dashboard_redirects_when_not_logged_in(self):
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertRedirects(resp, reverse("portal:login"))

    def test_login_with_correct_credentials_succeeds(self):
        resp = self.client.post(reverse("portal:login"), {
            "username": "client1", "password": "clientpass",
        })
        self.assertRedirects(resp, reverse("portal:dashboard"))

    def test_login_with_wrong_password_fails(self):
        resp = self.client.post(reverse("portal:login"), {
            "username": "client1", "password": "WRONG",
        })
        self.assertEqual(resp.status_code, 200)  # يفضل في نفس الصفحة
        self.assertFalse(self.client.session.get("portal_subscriber_id"))

    def test_dashboard_shows_own_data_after_login(self):
        self.client.post(reverse("portal:login"), {"username": "client1", "password": "clientpass"})
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertContains(resp, "عميل تجربة")

    def test_another_subscriber_cannot_see_first_ones_data(self):
        Subscriber.objects.create(
            company=self.company, full_name="عميل تاني", username="client2",
            password="pass2", plan=self.plan,
        )
        self.client.post(reverse("portal:login"), {"username": "client2", "password": "pass2"})
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertContains(resp, "عميل تاني")
        self.assertNotContains(resp, "عميل تجربة")
