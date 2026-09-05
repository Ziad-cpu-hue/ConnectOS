# ConnectOS — نظام إدارة اشتراكات إنترنت (SaaS)

مشروع Django كامل وشغّال فعليًا، بلوحة تحكم عربية 100%، لإدارة أجهزة
الميكروتيك، المشتركين، الباقات، الكروت، الفوترة، والتنبيهات. **31 اختبار
آلي حقيقي**، فحص أمان إنتاج نظيف 100% (`manage.py check --deploy`)، وكل
ميزة موثّقة هنا اتجربت بتشغيل فعلي مش بس قراءة كود.

---

## 🚀 التشغيل للتطوير المحلي

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo   # بيانات تجريبية (اختياري)
python manage.py test        # تشغيل الـ 31 اختبار
python manage.py runserver
```

افتح: **http://127.0.0.1:8000**

| المستخدم | كلمة المرور | الصلاحية |
|---|---|---|
| `owner` | `owner12345` | صاحب شبكة |
| `admin` | `admin12345` | مدير منصة |

بوابة العميل النهائي: **http://127.0.0.1:8000/portal/** (تسجّل مشترك من لوحة التحكم أولًا، وادخل ببياناته).

---

## 🏭 التشغيل للإنتاج الفعلي

```bash
cp .env.example .env    # واملأ القيم الحقيقية
pip install -r requirements.txt -r requirements-prod.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn connectos.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

- أمثلة إعدادات جاهزة موجودة في مجلد `deploy/`: `nginx.conf.example`،
  `connectos.service.example` (systemd)، `crontab.example`.
- `Procfile` موجود لو هتنشر على Heroku/Railway/Render.
- **تحقق دايمًا قبل أي إطلاق فعلي**: `python manage.py check --deploy`
  (لازم يطلع "System check identified no issues" بعد ما تملأ `.env`).

### متغيرات البيئة (`.env.example` فيه شرح كامل)
أهمها: `DJANGO_SECRET_KEY`، `DJANGO_DEBUG=False`، `DJANGO_ALLOWED_HOSTS`،
`DB_ENGINE=postgresql` + بيانات القاعدة، `EMAIL_HOST` (لصفحة نسيت كلمة
المرور)، ومفاتيح `PAYMOB_*` (اختياري — الدفع بيتعطّل بلطف من غيرها).

---

## 🌐 خريطة الموقع

| الرابط | مين يشوفه |
|---|---|
| `/` | **الجميع** — صفحة الهبوط، **لم تُعدَّل إطلاقًا طوال كل التحديثات** |
| `/signup/`, `/login/`, `/password-reset/` | الجميع |
| `/dashboard/` وكل شاشات الإدارة | بعد تسجيل دخول صاحب الشركة |
| `/dashboard/platform/` | **مدير المنصة فقط** (محمي على مستوى الـ view، ثغرة أمنية سابقة تم إصلاحها ومختبرة) |
| `/portal/` | **المشترك النهائي** (جلسة منفصلة تمامًا عن حسابات الشركة) |
| `/radius/accounting/` | أجهزة NAS فقط (بمفتاح سري) |
| `/payments/webhook/paymob/` | Paymob فقط (HMAC موقّع) |

---

## 📦 هيكل المشروع

```
connectos/
├── core/            → المستخدمين، الشركات، الدخول، استعادة كلمة المرور، سجل التدقيق
├── nas_manager/     → إدارة الأجهزة + RouterOS API حقيقي + sync لـ radius_core
├── subscribers/     → المشتركون الدائمون + sync فوري لـ RADIUS + أمر تنبيه الانتهاء
├── radius_core/     → جسر RADIUS (radcheck/radreply/nas/radacct متوافقة مع FreeRADIUS) + Accounting webhook
├── plans/           → إدارة الباقات
├── vouchers/        → توليد الكروت + مصمم سحب وإفلات + QR حقيقي
├── debts/           → الموزعون وحركات الديون
├── notifications/   → تنبيهات تيليجرام (شغّالة فعليًا بتوكن حقيقي)
├── payments/        → بوابة دفع Paymob (شركة + مشترك)
├── portal/          → 🆕 بوابة العميل النهائي (self-service منفصلة تمامًا)
├── dashboard/        → الشاشة الرئيسية + شاشة صاحب المنصة (محمية)
├── deploy/           → 🆕 أمثلة Nginx / systemd / crontab
├── templates/        → القالب المشترك (landing.html بدون أي تغيير)
├── requirements.txt / requirements-prod.txt / .env.example / Procfile  → 🆕
└── manage.py
```

---

## ✅ حالة الجاهزية الحالية

| المحور | الحالة |
|---|---|
| لوحة إدارة كاملة (CRUD، تصميم، UI) | ✅ ناضجة |
| عزل بيانات الشركات (Multi-tenancy) | ✅ مُختبَر آليًا |
| الثغرة الأمنية الحرجة | ✅ مُصلَحة ومُختبَرة (regression test) |
| بوابة العميل النهائي (self-service) | ✅ شغّالة (تسجيل دخول، استهلاك، تجديد) |
| جسر RADIUS (الكود والمنطق) | ✅ صحيح ومتوافق مع سكيمة FreeRADIUS القياسية |
| اختبار مع جهاز ميكروتيك حقيقي | ⚠️ الكود صحيح، لسه محتاج جهاز فعلي للتأكيد النهائي |
| بوابة الدفع Paymob | ✅ الكود جاهز 100%، محتاج مفاتيح حساب تاجر حقيقي للتفعيل |
| تنبيهات تيليجرام | ✅ شغّالة فعليًا بمجرد توكن حقيقي |
| اختبارات آلية | ✅ 31 اختبار، كلهم ناجحين |
| جاهزية الإنتاج | ✅ `check --deploy` نظيف 100%، Gunicorn مُختبَر فعليًا |
| نسخ احتياطي دوري / Celery للمهام الدورية | ⚠️ استُبدل بأمر `notify_expiring_subscribers` يدوي عبر cron (كافٍ للحجم الحالي) |

**الخلاصة**: المشروع بقى فعليًا في مرحلة "جاهز لتجربة حقيقية محدودة (Pilot)"
مع عميل واحد وجهاز ميكروتيك حقيقي — وده الاختبار الوحيد المتبقي اللي مش
ممكن يتم من غير بيئة فعلية على أرض الواقع.
