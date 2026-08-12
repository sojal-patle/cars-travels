
import os, uuid, hmac, hashlib, smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import razorpay
except ImportError:
    razorpay = None

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

db_url = os.getenv("DATABASE_URL", "sqlite:///travel.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Setting(db.Model):
    id=db.Column(db.Integer, primary_key=True); key=db.Column(db.String(80), unique=True); value=db.Column(db.Text)

class Vehicle(db.Model):
    id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(120),nullable=False)
    category=db.Column(db.String(60)); seats=db.Column(db.Integer); price_per_km=db.Column(db.Float)
    image=db.Column(db.Text); description=db.Column(db.Text); active=db.Column(db.Boolean,default=True)

class Package(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(150)); location=db.Column(db.String(100))
    days=db.Column(db.String(80)); price=db.Column(db.Float); image=db.Column(db.Text); description=db.Column(db.Text); active=db.Column(db.Boolean,default=True)

class Booking(db.Model):
    id=db.Column(db.Integer,primary_key=True); booking_code=db.Column(db.String(40),unique=True)
    vehicle_id=db.Column(db.Integer,db.ForeignKey("vehicle.id")); vehicle=db.relationship("Vehicle")
    customer_name=db.Column(db.String(120)); phone=db.Column(db.String(40)); email=db.Column(db.String(160))
    pickup=db.Column(db.String(160)); destination=db.Column(db.String(160)); start_date=db.Column(db.String(20)); end_date=db.Column(db.String(20))
    passengers=db.Column(db.Integer); distance=db.Column(db.Float); total=db.Column(db.Float); status=db.Column(db.String(30),default="Pending")
    payment_status=db.Column(db.String(30),default="Unpaid"); razorpay_order_id=db.Column(db.String(100)); razorpay_payment_id=db.Column(db.String(100))
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

class Review(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120)); rating=db.Column(db.Integer); comment=db.Column(db.Text)
    approved=db.Column(db.Boolean,default=False); created_at=db.Column(db.DateTime,default=datetime.utcnow)

class Inquiry(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120)); phone=db.Column(db.String(40)); email=db.Column(db.String(160))
    destination=db.Column(db.String(160)); travel_date=db.Column(db.String(20)); people=db.Column(db.Integer); message=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

DEFAULTS={
 "site_name":"Your Cars & Travels","tagline":"Reliable vehicles. Comfortable journeys. Memorable trips.",
 "phone":"+91 98765 43210","whatsapp":"919876543210","email":"hello@example.com",
 "address":"Your Business Address, Nagpur","currency":"₹","admin_password":os.getenv("INITIAL_ADMIN_PASSWORD","admin123")
}
def site_settings():
    return {x.key:x.value for x in Setting.query.all()}
@app.context_processor
def inject(): return {"site":site_settings(),"year":datetime.now().year,"razorpay_enabled":bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))}

def send_email(subject, body, to):
    host,user,pwd=os.getenv("SMTP_HOST"),os.getenv("SMTP_USER"),os.getenv("SMTP_PASSWORD")
    if not all([host,user,pwd,to]): return False
    try:
        msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=user; msg["To"]=to; msg.set_content(body)
        with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=15) as s:
            s.starttls(); s.login(user,pwd); s.send_message(msg)
        return True
    except Exception as e: print("EMAIL:",e); return False

def seed():
    db.create_all()
    for k,v in DEFAULTS.items():
        if not Setting.query.filter_by(key=k).first(): db.session.add(Setting(key=k,value=v))
    if not Vehicle.query.first():
        data=[
        ("Innova Crysta","SUV",7,22,"https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1200&q=85","Premium AC family/outstation vehicle with spacious luggage area."),
        ("Toyota Sedan","Sedan",4,16,"https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1200&q=85","Comfortable sedan for city, airport and outstation travel."),
        ("Tempo Traveller","Traveller",12,30,"https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1200&q=85","Spacious group-travel vehicle for families and friends."),
        ("Luxury SUV","Luxury",6,40,"https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?auto=format&fit=crop&w=1200&q=85","Premium SUV for corporate and luxury travel.")]
        for x in data: db.session.add(Vehicle(name=x[0],category=x[1],seats=x[2],price_per_km=x[3],image=x[4],description=x[5]))
    if not Package.query.first():
        data=[("Goa Escape","Goa","4 Days / 3 Nights",18999,"https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=85","Beach, sightseeing and flexible private travel."),
        ("Manali Adventure","Manali","5 Days / 4 Nights",24999,"https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1200&q=85","Mountain views, sightseeing and comfortable travel."),
        ("Rajasthan Heritage","Rajasthan","6 Days / 5 Nights",29999,"https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=1200&q=85","Fort, palace and cultural tour experience.")]
        for x in data: db.session.add(Package(title=x[0],location=x[1],days=x[2],price=x[3],image=x[4],description=x[5]))
    if not Review.query.first():
        for x in [("Amit Sharma",5,"Excellent vehicle and very professional driver."),("Priya Verma",5,"Smooth booking and a comfortable family trip."),("Rahul Patil",4,"Good service and clean vehicle.")]:
            db.session.add(Review(name=x[0],rating=x[1],comment=x[2],approved=True))
    db.session.commit()

@app.route("/")
def home(): return render_template("index.html",vehicles=Vehicle.query.filter_by(active=True).limit(4).all(),packages=Package.query.filter_by(active=True).limit(3).all(),reviews=Review.query.filter_by(approved=True).order_by(Review.id.desc()).limit(6).all())
@app.route("/vehicles")
def vehicles():
    q=request.args.get("q",""); cat=request.args.get("category",""); query=Vehicle.query.filter_by(active=True)
    if q: query=query.filter(db.or_(Vehicle.name.ilike(f"%{q}%"),Vehicle.category.ilike(f"%{q}%")))
    if cat: query=query.filter_by(category=cat)
    return render_template("vehicles.html",vehicles=query.all(),q=q,category=cat)
@app.route("/packages")
def packages(): return render_template("packages.html",packages=Package.query.filter_by(active=True).all())

@app.route("/availability")
def availability():
    start=request.args.get("start_date",""); end=request.args.get("end_date","") or start
    booked=set()
    if start:
        booked={b.vehicle_id for b in Booking.query.filter(Booking.status!="Cancelled",Booking.start_date<=end,db.or_(Booking.end_date=="",Booking.end_date>=start)).all()}
    return render_template("availability.html",vehicles=Vehicle.query.filter_by(active=True).all(),booked=booked,start=start,end=end)

def calc(v,d): return round(d*v.price_per_km+(1000 if d>300 else 500),2)

@app.route("/book/<int:vehicle_id>",methods=["GET","POST"])
def book(vehicle_id):
    v=Vehicle.query.get_or_404(vehicle_id)
    if request.method=="POST":
        f=request.form
        try:
            d=float(f["distance"]); p=int(f["passengers"])
            if d<=0 or p<1: raise ValueError
            b=Booking(booking_code="CT-"+uuid.uuid4().hex[:8].upper(),vehicle=v,customer_name=f["customer_name"],phone=f["phone"],email=f.get("email",""),
            pickup=f["pickup"],destination=f["destination"],start_date=f["start_date"],end_date=f.get("end_date",""),passengers=p,distance=d,total=calc(v,d))
            db.session.add(b); db.session.commit()
            s=site_settings()
            body=f"""New booking {b.booking_code}\nCustomer: {b.customer_name}\nPhone: {b.phone}\nEmail: {b.email}\nVehicle: {v.name}\nRoute: {b.pickup} -> {b.destination}\nDates: {b.start_date} -> {b.end_date}\nPassengers: {p}\nEstimated total: {s['currency']}{b.total:.0f}"""
            send_email(f"New booking {b.booking_code}",body,s.get("email"))
            if b.email: send_email(f"Booking received - {b.booking_code}","Your booking request was received. Booking ID: "+b.booking_code,b.email)
            return redirect(url_for("payment",booking_code=b.booking_code))
        except Exception as e:
            print("BOOK:",e); db.session.rollback(); flash("Please enter valid booking details.")
    return render_template("book.html",vehicle=v)

@app.route("/payment/<booking_code>")
def payment(booking_code):
    b=Booking.query.filter_by(booking_code=booking_code).first_or_404()
    if not razorpay_enabled(): return render_template("payment.html",booking=b,enabled=False)
    client=razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"),os.getenv("RAZORPAY_KEY_SECRET")))
    if not b.razorpay_order_id:
        order=client.order.create({"amount":int(round(b.total*100)),"currency":"INR","receipt":b.booking_code,"payment_capture":1})
        b.razorpay_order_id=order["id"]; db.session.commit()
    return render_template("payment.html",booking=b,enabled=True,key_id=os.getenv("RAZORPAY_KEY_ID"))

def razorpay_enabled(): return bool(razorpay and os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))

@app.route("/payment/verify",methods=["POST"])
def payment_verify():
    if not razorpay_enabled(): return jsonify(ok=False,error="Payment gateway not configured"),400
    f=request.form; b=Booking.query.filter_by(booking_code=f["booking_code"]).first_or_404()
    msg=(f["razorpay_order_id"]+"|"+f["razorpay_payment_id"]).encode()
    expected=hmac.new(os.getenv("RAZORPAY_KEY_SECRET").encode(),msg,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,f["razorpay_signature"]): return jsonify(ok=False,error="Signature verification failed"),400
    b.payment_status="Paid"; b.status="Confirmed"; b.razorpay_payment_id=f["razorpay_payment_id"]; db.session.commit()
    s=site_settings(); send_email("Payment received - "+b.booking_code,f"Payment successful.\nBooking: {b.booking_code}\nAmount: {s['currency']}{b.total:.0f}\nPayment ID: {b.razorpay_payment_id}",s.get("email"))
    if b.email: send_email("Payment confirmed - "+b.booking_code,"Your payment was successfully verified. Booking ID: "+b.booking_code,b.email)
    return jsonify(ok=True,redirect=url_for("confirmation",booking_code=b.booking_code))

@app.route("/confirmation/<booking_code>")
def confirmation(booking_code): return render_template("confirmation.html",booking=Booking.query.filter_by(booking_code=booking_code).first_or_404())

@app.route("/payment/webhook",methods=["POST"])
def payment_webhook():
    secret=os.getenv("RAZORPAY_WEBHOOK_SECRET",""); signature=request.headers.get("X-Razorpay-Signature","")
    if secret and not hmac.compare_digest(hmac.new(secret.encode(),request.data,hashlib.sha256).hexdigest(),signature): return "invalid",400
    data=request.get_json(silent=True) or {}; p=data.get("payload",{}).get("payment",{}).get("entity",{})
    oid=p.get("order_id")
    if oid:
        b=Booking.query.filter_by(razorpay_order_id=oid).first()
        if b and p.get("status")=="captured": b.payment_status="Paid"; b.status="Confirmed"; db.session.commit()
    return "ok",200

@app.route("/reviews",methods=["GET","POST"])
def reviews():
    if request.method=="POST":
        f=request.form; db.session.add(Review(name=f["name"],rating=int(f["rating"]),comment=f["comment"])); db.session.commit(); flash("Review submitted for approval."); return redirect(url_for("reviews"))
    return render_template("reviews.html",reviews=Review.query.filter_by(approved=True).order_by(Review.id.desc()).all())

@app.route("/contact",methods=["GET","POST"])
def contact():
    if request.method=="POST":
        f=request.form; i=Inquiry(name=f["name"],phone=f["phone"],email=f.get("email",""),destination=f.get("destination",""),travel_date=f.get("travel_date",""),people=int(f.get("people") or 1),message=f.get("message","")); db.session.add(i); db.session.commit()
        s=site_settings(); send_email("New travel inquiry",f"Name: {i.name}\nPhone: {i.phone}\nEmail: {i.email}\nDestination: {i.destination}\nDate: {i.travel_date}\nPeople: {i.people}\nMessage: {i.message}",s.get("email")); flash("Message sent! We will contact you soon."); return redirect(url_for("contact"))
    return render_template("contact.html")

def admin_required(): return session.get("admin")
@app.route("/admin",methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("password")!=site_settings().get("admin_password"): flash("Invalid password."); return redirect(url_for("admin"))
        session["admin"]=True
    if not admin_required(): return render_template("admin_login.html")
    stats={"vehicles":Vehicle.query.filter_by(active=True).count(),"bookings":Booking.query.count(),"customers":len({b.phone for b in Booking.query.all()}),"revenue":sum(b.total or 0 for b in Booking.query.filter(Booking.status!="Cancelled").all())}
    return render_template("admin.html",stats=stats,bookings=Booking.query.order_by(Booking.id.desc()).limit(30).all(),inquiries=Inquiry.query.order_by(Inquiry.id.desc()).limit(30).all(),vehicles=Vehicle.query.order_by(Vehicle.id.desc()).all(),packages=Package.query.order_by(Package.id.desc()).all(),reviews=Review.query.order_by(Review.id.desc()).all())

@app.route("/admin/logout")
def logout(): session.clear(); return redirect(url_for("admin"))
@app.route("/admin/settings",methods=["POST"])
def admin_settings():
    if not admin_required(): return redirect(url_for("admin"))
    for k in DEFAULTS:
        if k in request.form:
            if k=="admin_password" and not request.form[k]: continue
            x=Setting.query.filter_by(key=k).first(); x.value=request.form[k]
    db.session.commit(); flash("Website settings updated."); return redirect(url_for("admin"))
@app.route("/admin/vehicle/save",methods=["POST"])
def vehicle_save():
    if not admin_required(): return redirect(url_for("admin"))
    f=request.form; v=Vehicle.query.get(int(f["id"])) if f.get("id") else Vehicle()
    v.name=f["name"]; v.category=f["category"]; v.seats=int(f["seats"]); v.price_per_km=float(f["price_per_km"]); v.image=f["image"]; v.description=f["description"]; v.active=True
    db.session.add(v); db.session.commit(); return redirect(url_for("admin"))
@app.route("/admin/vehicle/delete/<int:i>")
def vehicle_delete(i):
    if not admin_required(): return redirect(url_for("admin"))
    v=Vehicle.query.get_or_404(i); v.active=False; db.session.commit(); return redirect(url_for("admin"))
@app.route("/admin/package/save",methods=["POST"])
def package_save():
    if not admin_required(): return redirect(url_for("admin"))
    f=request.form; p=Package.query.get(int(f["id"])) if f.get("id") else Package()
    p.title=f["title"]; p.location=f["location"]; p.days=f["days"]; p.price=float(f["price"]); p.image=f["image"]; p.description=f["description"]; p.active=True
    db.session.add(p); db.session.commit(); return redirect(url_for("admin"))
@app.route("/admin/review/<int:i>/<action>")
def review_action(i,action):
    if not admin_required(): return redirect(url_for("admin"))
    r=Review.query.get_or_404(i); r.approved=(action=="approve"); db.session.commit(); return redirect(url_for("admin"))
@app.route("/admin/booking/<int:i>/<status>")
def booking_status(i,status):
    if not admin_required() or status not in ["Pending","Confirmed","Completed","Cancelled"]: return redirect(url_for("admin"))
    b=Booking.query.get_or_404(i); b.status=status; db.session.commit(); return redirect(url_for("admin"))

@app.route("/health")
def health(): return jsonify(status="ok",database="connected")

with app.app_context(): seed()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=False)
