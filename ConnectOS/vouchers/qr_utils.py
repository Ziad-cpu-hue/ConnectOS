"""توليد QR Code فعلي (مش رابط وهمي) لكل كارت — العميل يمسحه بالكاميرا
فيتصل بالهوت سبوت مباشرة من غير ما يكتب اليوزر/الباسورد يدوي."""
import base64
from io import BytesIO

import qrcode


def voucher_qr_base64(voucher, hotspot_login_url="http://hotspot.local/login"):
    payload = f"{hotspot_login_url}?username={voucher.code}&password={voucher.code}"
    img = qrcode.make(payload, box_size=4, border=1)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
