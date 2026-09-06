from django.test import TestCase
from django.urls import reverse

from core.models import Company, User
from plans.models import Plan
from radius_core.models import RadCheck, RadReply
from subscribers.models import Subscriber


class SubscriberRadiusSyncTests(TestCase):
    """أهم اختبار في المشروع كله: التأكد إن أي حفظ/حذف لمشترك بينعكس فورًا
    وبشكل صحيح على جداول RADIUS الحقيقية (radcheck/radreply)."""

    def setUp(self):
        self.company = Company.objects.create(name="شركة تجربة")
        self.plan = Plan.objects.create(
            company=self.company, name="باقة 2 ميجا", duration_days=30,
            speed_limit_kbps=2048, price=100,
        )

    def test_save_creates_radcheck_password_row(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed1",
            password="secret123", plan=self.plan,
        )
        row = RadCheck.objects.get(username="ahmed1", attribute="Cleartext-Password")
        self.assertEqual(row.value, "secret123")

    def test_plan_speed_syncs_to_radreply_rate_limit(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed2",
            password="secret123", plan=self.plan,
        )
        row = RadReply.objects.get(username="ahmed2", attribute="Mikrotik-Rate-Limit")
        self.assertEqual(row.value, "2048k/2048k")

    def test_suspended_subscriber_gets_reject_in_radcheck(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed3",
            password="secret123", plan=self.plan, status="suspended",
        )
        self.assertTrue(
            RadCheck.objects.filter(username="ahmed3", attribute="Auth-Type", value="Reject").exists()
        )

    def test_reactivating_removes_reject_rule(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed4",
            password="secret123", plan=self.plan, status="suspended",
        )
        sub.status = "active"
        sub.save()
        self.assertFalse(
            RadCheck.objects.filter(username="ahmed4", attribute="Auth-Type").exists()
        )

    def test_delete_removes_all_radius_rows(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed5",
            password="secret123", plan=self.plan,
        )
        sub_id = sub.id
        sub.delete()
        self.assertFalse(RadCheck.objects.filter(username="ahmed5").exists())
        self.assertFalse(RadReply.objects.filter(username="ahmed5").exists())

    def test_renew_extends_expiry_by_plan_duration(self):
        sub = Subscriber.objects.create(
            company=self.company, full_name="أحمد", username="ahmed6",
            password="secret123", plan=self.plan,
        )
        self.assertIsNone(sub.expires_at)
        sub.renew()
        self.assertIsNotNone(sub.expires_at)
        self.assertEqual(sub.status, "active")


class SubscriberMultiTenancyTests(TestCase):
    """اختبار حرج: التأكد إن شركة تانية معندهاش أي وصول لمشتركين شركة غيرها،
    حتى لو حاولت تدخل الرابط مباشرة."""

    def setUp(self):
        self.company_a = Company.objects.create(name="شركة أ")
        self.company_b = Company.objects.create(name="شركة ب")
        self.plan_a = Plan.objects.create(company=self.company_a, name="باقة أ", duration_days=30, price=50)
        self.owner_a = User.objects.create_user(username="owner_a", password="pass12345", company=self.company_a, role="owner")
        self.owner_b = User.objects.create_user(username="owner_b", password="pass12345", company=self.company_b, role="owner")
        self.sub_a = Subscriber.objects.create(
            company=self.company_a, full_name="عميل شركة أ", username="client_a",
            password="pass", plan=self.plan_a,
        )

    def test_company_b_cannot_see_company_a_subscriber_in_list(self):
        self.client.login(username="owner_b", password="pass12345")
        resp = self.client.get(reverse("subscribers:list"))
        self.assertNotContains(resp, "عميل شركة أ")

    def test_company_b_cannot_edit_company_a_subscriber_directly(self):
        self.client.login(username="owner_b", password="pass12345")
        resp = self.client.get(reverse("subscribers:edit", args=[self.sub_a.pk]))
        self.assertEqual(resp.status_code, 404, "لازم ياخد 404 مش يشوف بيانات مشترك شركة تانية")

    def test_company_b_cannot_delete_company_a_subscriber(self):
        self.client.login(username="owner_b", password="pass12345")
        resp = self.client.post(reverse("subscribers:delete", args=[self.sub_a.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Subscriber.objects.filter(pk=self.sub_a.pk).exists(), "المشترك ميتحذفش")

    def test_company_a_can_manage_its_own_subscriber(self):
        self.client.login(username="owner_a", password="pass12345")
        resp = self.client.get(reverse("subscribers:list"))
        self.assertContains(resp, "عميل شركة أ")


class SubscriberSpeedPolicyTests(TestCase):
    """يتأكد إن سياسة السرعة الثلاثية (سقف ثابت / سرعة مفتوحة / توزيع عادل)
    فعلًا بتتطبق في radreply بمجرد حفظ المشترك — دي المشكلة اللي كانت
    الخيارات فيها مجرد checkboxes للشكل من غير أي تأثير فعلي."""

    def setUp(self):
        self.company = Company.objects.create(name="شركة السرعات")

    def test_flat_rate_plan_sets_mikrotik_rate_limit(self):
        plan = Plan.objects.create(
            company=self.company, name="باقة سقف ثابت", duration_days=30,
            speed_limit_kbps=1024, price=50,
        )
        sub = Subscriber.objects.create(
            company=self.company, full_name="مشترك 1", username="flat_user",
            password="pass", plan=plan,
        )
        reply = RadReply.objects.get(username=sub.username, attribute="Mikrotik-Rate-Limit")
        self.assertEqual(reply.value, "1024k/1024k")
        self.assertFalse(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Group").exists())

    def test_open_speed_plan_sets_no_speed_reply_at_all(self):
        plan = Plan.objects.create(
            company=self.company, name="باقة مفتوحة", duration_days=30,
            speed_limit_kbps=1024, allow_open_speed=True, price=80,
        )
        sub = Subscriber.objects.create(
            company=self.company, full_name="مشترك 2", username="open_user",
            password="pass", plan=plan,
        )
        self.assertFalse(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Rate-Limit").exists())
        self.assertFalse(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Group").exists())

    def test_fair_share_plan_sets_mikrotik_group_not_flat_rate(self):
        plan = Plan.objects.create(
            company=self.company, name="باقة توزيع عادل", duration_days=30,
            speed_limit_kbps=2048, speed_equation_enabled=True, price=70,
        )
        sub = Subscriber.objects.create(
            company=self.company, full_name="مشترك 3", username="fair_user",
            password="pass", plan=plan,
        )
        from radius_core.speed_policy import FAIR_SHARE_GROUP
        reply = RadReply.objects.get(username=sub.username, attribute="Mikrotik-Group")
        self.assertEqual(reply.value, FAIR_SHARE_GROUP)
        self.assertFalse(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Rate-Limit").exists())

    def test_switching_plan_speed_policy_clears_previous_reply(self):
        """لو الباقة اتغيّرت من سقف ثابت لسرعة مفتوحة، الـ reply القديم
        لازم يتشال مش يفضل متراكم مع الجديد."""
        plan_flat = Plan.objects.create(
            company=self.company, name="باقة أ", duration_days=30,
            speed_limit_kbps=512, price=30,
        )
        sub = Subscriber.objects.create(
            company=self.company, full_name="مشترك 4", username="switch_user",
            password="pass", plan=plan_flat,
        )
        self.assertTrue(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Rate-Limit").exists())

        plan_open = Plan.objects.create(
            company=self.company, name="باقة ب", duration_days=30,
            allow_open_speed=True, price=60,
        )
        sub.plan = plan_open
        sub.save()
        self.assertFalse(RadReply.objects.filter(username=sub.username, attribute="Mikrotik-Rate-Limit").exists())
