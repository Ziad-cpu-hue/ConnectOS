from django import forms
from django.contrib.auth.password_validation import validate_password

from core.models import Company, PlatformPlan, User


PLAN_PRICES = {
    "starter": 150,
    "growth": 450,
    "pro": 950,
}


class SignupForm(forms.Form):
    company_name = forms.CharField(
        label="اسم شبكتك", max_length=200,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "مثال: شبكة النور نت"}),
    )
    full_name = forms.CharField(
        label="اسمك بالكامل", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "الاسم اللي هيظهر في حسابك"}),
    )
    phone = forms.CharField(
        label="رقم الهاتف", max_length=20,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "01xxxxxxxxx"}),
    )
    plan = forms.ChoiceField(
        label="الخطة",
        choices=[("starter", "البداية — 150 ج/شهريًا"), ("growth", "النمو — 450 ج/شهريًا"), ("pro", "الاحتراف — 950 ج/شهريًا")],
        widget=forms.Select(attrs={"class": "field"}),
        initial="growth",
    )
    username = forms.CharField(
        label="اسم المستخدم", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "هتسجل دخولك بيه"}),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={"class": "field", "placeholder": "example@mail.com"}),
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": "field", "placeholder": "8 أحرف على الأقل"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم ده مستخدم بالفعل، جرّب اسم تاني.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self):
        plan = self.cleaned_data["plan"]
        company = Company.objects.create(
            name=self.cleaned_data["company_name"],
            owner_phone=self.cleaned_data["phone"],
            subscription_plan=plan,
            monthly_fee=PLAN_PRICES[plan],
            is_active=False,
        )
        names = self.cleaned_data["full_name"].split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
            phone=self.cleaned_data["phone"],
            company=company,
            role="owner",
        )
        return user


class SubscribeForm(forms.Form):
    """نموذج الاشتراك من صفحة الهبوط بعد اختيار باقة معينة من قسم "الباقات".
    نفس فكرة صفحة register/<id> بتاعة Smart Radius: اسم الشبكة، اسم المدير،
    رقم التليفون، يوزر/باسورد + تأكيد الباسورد — وبعدها بيتعمل حساب الشركة
    مربوط مباشرة بالباقة اللي اختارها (PlatformPlan) وفاتورة بانتظار الدفع."""

    network_name = forms.CharField(
        label="اسم الشبكة", max_length=200,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب اسم الشبكة"}),
    )
    manager_name = forms.CharField(
        label="اسم المدير", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب اسم المدير"}),
    )
    phone = forms.CharField(
        label="رقم التليفون", max_length=20,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب رقم التليفون"}),
    )
    username = forms.CharField(
        label="اسم المستخدم", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب اسم المستخدم"}),
    )
    password = forms.CharField(
        label="كلمة السر",
        widget=forms.PasswordInput(attrs={"class": "field", "placeholder": "اكتب كلمة السر"}),
    )
    password_confirm = forms.CharField(
        label="تأكيد كلمة السر",
        widget=forms.PasswordInput(attrs={"class": "field", "placeholder": "اكتب تأكيد كلمة السر"}),
    )

    def __init__(self, *args, plan=None, **kwargs):
        self.plan = plan
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم ده مستخدم بالفعل، جرّب اسم تاني.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        pw, pw2 = cleaned.get("password"), cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "كلمة السر وتأكيدها مش متطابقين.")
        return cleaned

    def save(self):
        company = Company.objects.create(
            name=self.cleaned_data["network_name"],
            owner_phone=self.cleaned_data["phone"],
            platform_plan=self.plan,
            subscription_plan="starter",  # الحقل القديم بقى غير مستخدم فعليًا مع الباقات الجديدة
            monthly_fee=self.plan.price_monthly,
            is_active=False,  # بيتفعّل بعد تأكيد المدير لاستلام الدفع
        )
        names = self.cleaned_data["manager_name"].split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
            phone=self.cleaned_data["phone"],
            company=company,
            role="owner",
        )
        from .models import PlatformPayment
        invoice = PlatformPayment.objects.create(
            company=company,
            amount=self.plan.price_monthly,
            method="محفظة إلكترونية",
            is_confirmed=False,
        )
        return user, invoice


class JoinSubAccountForm(forms.Form):
    """فورم الموظف اللي بيدخل بكود انضمام صاحب الشبكة عطاله، بدل ما يوزر
    وباسورد يتكتبوله يدوي. نفس فورم SubscribeForm تقريبًا بس من غير باقة —
    لأن الموظف بينضم لشركة موجودة بالفعل مش بيعمل شركة جديدة."""

    full_name = forms.CharField(
        label="الاسم بالكامل", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب اسمك بالكامل"}),
    )
    phone = forms.CharField(
        label="رقم التليفون", max_length=20, required=False,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب رقم التليفون"}),
    )
    username = forms.CharField(
        label="اسم المستخدم", max_length=150,
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "اكتب اسم المستخدم"}),
    )
    password = forms.CharField(
        label="كلمة السر",
        widget=forms.PasswordInput(attrs={"class": "field", "placeholder": "اكتب كلمة السر"}),
    )
    password_confirm = forms.CharField(
        label="تأكيد كلمة السر",
        widget=forms.PasswordInput(attrs={"class": "field", "placeholder": "اكتب تأكيد كلمة السر"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم ده مستخدم بالفعل، جرّب اسم تاني.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        pw, pw2 = cleaned.get("password"), cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "كلمة السر وتأكيدها مش متطابقين.")
        return cleaned

    def save(self, invite):
        names = self.cleaned_data["full_name"].split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
            phone=self.cleaned_data.get("phone", ""),
            company=invite.company,
            role=invite.role,
        )
        from django.utils import timezone
        invite.used_by = user
        invite.used_at = timezone.now()
        invite.is_active = False
        invite.save(update_fields=["used_by", "used_at", "is_active"])
        return user
