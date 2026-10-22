# Maktab IT portal
Flask + SQLAlchemy. Lokal: `py -m venv .venv`, `.venv\\Scripts\\activate`, `pip install -r requirements.txt`, `python app.py`.
Birinchi adminni yaratish uchun `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY` environment variables belgilang. Render'da Web Service → Environment bo‘limida sozlang. Admin login birinchi ishga tushishda yaratiladi. Parolni GitHub'ga hech qachon yozmang.
Foydalanuvchi `/register` orqali ro‘yxatdan o‘tadi, admin `/admin/users` da tasdiqlaydi yoki o‘chiradi. Tasdiqlangan oddiy foydalanuvchi `/userfeed` orqali murojaat yuboradi va o‘z murojaatlarini ko‘radi.
Eslatma: bu mustaqil prototip, rasmiy e-Maktab mahsuloti emas. Production uchun CSRF himoyasi, xavfsizlik auditi, migratsiyalar va zaxira nusxalari kerak.
