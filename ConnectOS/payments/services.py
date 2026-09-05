"""
تكامل حقيقي مع Paymob (أكبر بوابة دفع إلكتروني في مصر، وبتغطي فودافون كاش
وفوري وبطاقات البنوك من واجهة واحدة — نفس الفكرة اللي شرحناها قبل كده).
التدفق الرسمي لـ Paymob 3 خطوات (Auth Token → Order → Payment Key)، وده
منفّذ هنا بالظبط زي التوثيق الرسمي. محتاج فقط مفاتيح حساب Paymob حقيقية في
متغيرات البيئة عشان يشتغل فعليًا (PAYMOB_API_KEY, PAYMOB_INTEGRATION_ID,
PAYMOB_IFRAME_ID, PAYMOB_HMAC_SECRET)."""
import hashlib
import hmac as hmac_lib

import requests
from django.conf import settings

BASE_URL = "https://accept.paymob.com/api"


class PaymobNotConfigured(Exception):
    pass


class PaymobService:
    def __init__(self):
        if not settings.PAYMOB_API_KEY:
            raise PaymobNotConfigured("مفاتيح Paymob غير مضبوطة في متغيرات البيئة.")
        self.api_key = settings.PAYMOB_API_KEY
        self.integration_id = settings.PAYMOB_INTEGRATION_ID
        self.iframe_id = settings.PAYMOB_IFRAME_ID
        self.hmac_secret = settings.PAYMOB_HMAC_SECRET

    def _auth_token(self):
        r = requests.post(f"{BASE_URL}/auth/tokens", json={"api_key": self.api_key}, timeout=10)
        r.raise_for_status()
        return r.json()["token"]

    def _create_order(self, token, amount_cents, merchant_order_id):
        r = requests.post(
            f"{BASE_URL}/ecommerce/orders",
            json={
                "auth_token": token,
                "delivery_needed": False,
                "amount_cents": amount_cents,
                "currency": "EGP",
                "merchant_order_id": merchant_order_id,
                "items": [],
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["id"]

    def _payment_key(self, token, order_id, amount_cents, billing_data):
        r = requests.post(
            f"{BASE_URL}/acceptance/payment_keys",
            json={
                "auth_token": token,
                "amount_cents": amount_cents,
                "expiration": 3600,
                "order_id": order_id,
                "billing_data": billing_data,
                "currency": "EGP",
                "integration_id": self.integration_id,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["token"]

    def create_payment_iframe_url(self, transaction):
        """يرجع رابط الـ iframe اللي هيتحط في صفحة الدفع للعميل."""
        token = self._auth_token()
        amount_cents = int(transaction.amount * 100)
        order_id = self._create_order(token, amount_cents, merchant_order_id=f"connectos-{transaction.id}")
        billing_data = {
            "first_name": transaction.company.name or "N/A",
            "last_name": "N/A",
            "email": "billing@example.com",
            "phone_number": "+201000000000",
            "apartment": "N/A", "floor": "N/A", "street": "N/A", "building": "N/A",
            "shipping_method": "N/A", "postal_code": "N/A", "city": "N/A",
            "country": "N/A", "state": "N/A",
        }
        payment_token = self._payment_key(token, order_id, amount_cents, billing_data)
        transaction.provider_order_id = str(order_id)
        transaction.save(update_fields=["provider_order_id"])
        return f"https://accept.paymob.com/api/acceptance/iframes/{self.iframe_id}?payment_token={payment_token}"

    def verify_webhook_hmac(self, request_data, received_hmac):
        """تحقق من توقيع الـ HMAC اللي Paymob بيبعته مع كل webhook، عشان نتأكد
        إن الطلب فعلاً جاي منهم مش من حد بيحاول يزور عملية دفع ناجحة."""
        ordered_keys = [
            "amount_cents", "created_at", "currency", "error_occured",
            "has_parent_transaction", "id", "integration_id", "is_3d_secure",
            "is_auth", "is_capture", "is_refunded", "is_standalone_payment",
            "is_voided", "order", "owner", "pending", "source_data_pan",
            "source_data_sub_type", "source_data_type", "success",
        ]
        concatenated = "".join(str(request_data.get(k, "")) for k in ordered_keys)
        calculated = hmac_lib.new(
            self.hmac_secret.encode(), concatenated.encode(), hashlib.sha512
        ).hexdigest()
        return hmac_lib.compare_digest(calculated, received_hmac or "")
