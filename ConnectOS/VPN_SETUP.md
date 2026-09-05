# تجهيز سيرفر VPN حقيقي لميزة "فتح الأجهزة"

## الوضع الحالي بأمانة
ConnectOS بيولّد يوزر/باسورد/بورت نفق فريد لكل جهاز ميكروتك تلقائيًا (`NASServer.ensure_vpn_credentials`)،
وبيحط سطر SSTP client في سكريبت التركيب (`nas_manager:setup_script`)، وعنده صفحة "فتح الأجهزة" بتعرض
البيانات دي. **الجزء ده كله حقيقي وشغال ومُختبر.**

لكن عشان الاتصال يشتغل فعليًا (يعني تقدر فعلاً تفتح Winbox على راوتر خلف NAT من بعيد)، لازم يكون
في سيرفر VPN حقيقي شغال بيستقبل اتصالات SSTP دي على الدومين اللي حطيته في `VPN_PUBLIC_HOST`.
ده مش حاجة كود Django بيقدر يعملها لوحده — محتاج سيرفر فعلي (VPS) بتجهزه مرة واحدة.

## الخيار المقترح: SoftEther VPN Server
بيدعم SSTP built-in، ومجاني، ومناسب لعدد كبير من الاتصالات المتزامنة.

### 1) تثبيت السيرفر (على Ubuntu VPS مثلاً)
```bash
sudo apt update && sudo apt install -y build-essential
wget https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/latest/download/softether-vpnserver-linux-x64-64bit.tar.gz
tar xzf softether-vpnserver-linux-x64-64bit.tar.gz
cd vpnserver
make
sudo mv ../vpnserver /usr/local/
sudo /usr/local/vpnserver/vpnserver start
```

### 2) الإعداد الأساسي عبر `vpncmd`
```bash
sudo /usr/local/vpnserver/vpncmd localhost /server
# داخل vpncmd:
ServerPasswordSet   # حط باسورد الإدارة
HubCreate CONNECTOS_HUB /PASSWORD:changeme
Hub CONNECTOS_HUB
SecureNatEnable      # يوزع IPs افتراضية تلقائيًا لكل جهاز يتصل
```

### 3) تفعيل SSTP (ده اللي RouterOS بيتكلم بيه)
داخل نفس الـ Hub:
```
OnlineSetEnable
```
SoftEther بيفعّل SSTP تلقائيًا على بورت 443 بمجرد ما يكون عنده شهادة SSL صحيحة على الدومين
(استخدم Let's Encrypt عادي، أو الشهادة الافتراضية للتجربة).

### 4) ربط كل جهاز بيوزر مستقل
لكل `NASServer` عندك يوزر/باسورد اتولد أوتوماتيك (`vpn_username` / `vpn_password`).
تقدر تضيفهم لـ Hub تلقائيًا بكود Python بسيط بيستخدم SoftEther RPC API (JSON-RPC على HTTPS)،
أو تعمل management command في Django بيعمل sync دوري بين جدول `NASServer` وقائمة يوزرات الـ Hub.
مثال مبسط (يحتاج مكتبة `softether-python` أو استدعاء `vpncmd` مباشرة عبر `subprocess`):
```bash
UserCreate {{vpn_username}} /GROUP:none /REALNAME:none /NOTE:none
UserPasswordSet {{vpn_username}} /PASSWORD:{{vpn_password}}
```

### 5) الوصول للراوتر عبر البورت المخصص
بعد ما الجهاز يتصل وياخد IP افتراضي جوه الـ Hub، تقدر تعمل port-forward على مستوى Nginx stream
(أو HAProxy) من `VPN_PUBLIC_HOST:{{vpn_tunnel_port}}` لـ IP الراوتر الافتراضي جوه الـ VPN على بورت
Winbox (8291) أو API (8728). مثال Nginx stream block لكل جهاز:
```nginx
stream {
    server {
        listen 8214;
        proxy_pass 10.10.0.5:8728;  # الـ IP الافتراضي اللي الراوتر ده اخده جوه الـ VPN
    }
}
```
البورت `8214` ده نفس القيمة المتولدة في `NASServer.vpn_tunnel_port` — يعني تقدر تولّد ملفات
إعداد Nginx دي أوتوماتيك من Django (management command يقرأ كل الأجهزة ويكتب ملف conf ويعمل reload).

## الخلاصة
- طبقة البيانات والواجهة في ConnectOS: **جاهزة 100%**.
- ربطها بسيرفر VPN حقيقي: **خطوة نشر (Deployment) لازم تتعمل مرة واحدة على السيرفر بتاعك**،
  مش كود Django إضافي. الخطوات فوق دي نقطة بداية عملية وليست مجرد وصف نظري.
