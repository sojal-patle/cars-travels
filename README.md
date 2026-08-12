# Cars & Travels — Production-Ready Starter

A modern, responsive Cars & Travels booking platform built with Flask + SQLAlchemy.

## Included
- Premium responsive travel UI
- Vehicle search/catalogue
- Date availability
- Booking + automatic fare estimate
- Razorpay Standard Checkout integration
- Server-side Razorpay signature verification
- Razorpay webhook endpoint
- Payment/booking status
- Customer + business email notifications through SMTP
- WhatsApp click-to-chat
- Tour packages
- Reviews + moderation
- Custom trip inquiries
- Admin dashboard
- Website settings (name, phone, WhatsApp, email, address, currency)
- Vehicle/package management
- PostgreSQL support via DATABASE_URL
- SQLite fallback for local development
- Gunicorn production server
- Render deployment configuration
- Health endpoint `/health`

## Local run

Windows:
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Admin: http://127.0.0.1:5000/admin

For local development the default admin password is `admin123`; change it immediately in Admin Settings.

## Production

Do NOT use Flask's development server in production. Use Gunicorn or a hosting platform.

1. Push this project to a private GitHub repository.
2. Create a PostgreSQL database and copy its connection string into `DATABASE_URL`.
3. Deploy as a Python web service using:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
4. Set all variables from `.env.example` as hosting environment variables.
5. Add a custom domain and enable HTTPS.
6. Create a Razorpay account, complete KYC/business verification, generate Test API keys, test, then switch to Live API keys.
7. In Razorpay, create a webhook pointing to:
   `https://YOUR-DOMAIN/payment/webhook`
   and use the same `RAZORPAY_WEBHOOK_SECRET`.
8. Configure SMTP with a business email/app password.
9. Test a full booking: booking -> Razorpay order -> checkout -> signature verification -> confirmed booking -> webhook.

### Important payment security
- Never commit `.env` or API secrets to GitHub.
- Never expose `RAZORPAY_KEY_SECRET` in frontend code.
- Keep HTTPS enabled.
- Only treat a payment as successful after server-side verification / captured status.
