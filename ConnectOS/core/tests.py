from django.test import TestCase, Client
from django.urls import reverse

from core.models import Company, User


class SignupLoginTests(TestCase):
    def test_signup_creates_user_and_company_then_logs_in(self):
        resp = self.client.post(reverse("core:signup"), {
            "company_name": "شركة تجربة",
            "full_name": "محمد أحمد",
            "phone": "01000000000",
            "plan": "growth",
            "username": "newowner",
            "email": "newowner@example.com",
            "password": "StrongPass123!",
        })
        user = User.objects.filter(username="newowner").first()
        self.assertIsNotNone(user, "المستخدم لازم يتسجل بعد الإرسال الصحيح")
        if user:
            self.assertIsNotNone(user.company_id, "المستخدم لازم يتربط بشركة تلقائيًا")
            self.assertEqual(user.role, "owner")
        # لازم يبقى اتسجل دخوله تلقائيًا وحوّل للوحة التحكم
        self.assertRedirects(resp, reverse("dashboard:home"))

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)  # لازم يحوّل لصفحة الدخول
        self.assertIn("/login/", resp.url)
