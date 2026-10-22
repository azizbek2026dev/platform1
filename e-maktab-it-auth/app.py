import os
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from models import db, User, Student, Lesson, JournalEntry, Equipment, Ticket

app=Flask(__name__)
app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY","local-dev-change-this-secret")
url=os.environ.get("DATABASE_URL","sqlite:///emaktab_it.db")
if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
app.config["SQLALCHEMY_DATABASE_URI"]=url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
app.config["SQLALCHEMY_ENGINE_OPTIONS"]={"pool_pre_ping":True}
db.init_app(app)

with app.app_context():
    db.create_all()
    au=os.environ.get("ADMIN_USERNAME")
    ap=os.environ.get("ADMIN_PASSWORD")
    if au and ap and not User.query.filter_by(username=au.lower()).first():
        u=User(username=au.strip().lower(),full_name="Administrator",role="admin",approved=True)
        u.set_password(ap); db.session.add(u); db.session.commit()

@app.context_processor
def globals_for_templates():
    u=db.session.get(User,session.get("user_id")) if session.get("user_id") else None
    return {"current_user":u}

def signed_in(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        u=db.session.get(User,session.get("user_id")) if session.get("user_id") else None
        if not u: return redirect(url_for("login"))
        if u.role!="admin" and not u.approved: return redirect(url_for("pending"))
        return fn(*a,**kw)
    return wrapped

def admin_only(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        u=db.session.get(User,session.get("user_id")) if session.get("user_id") else None
        if not u: return redirect(url_for("login"))
        if u.role!="admin": abort(403)
        return fn(*a,**kw)
    return wrapped

@app.template_filter("datefmt")
def datefmt(v): return v.strftime("%d.%m.%Y") if v else "—"

@app.route("/")
@signed_in
def home():
    u=db.session.get(User,session["user_id"])
    if u.role!="admin": return redirect(url_for("userfeed"))
    stats={"students":Student.query.count(),"equipment":Equipment.query.count(),
      "working":Equipment.query.filter_by(status="Soz").count(),
      "open_tickets":Ticket.query.filter(Ticket.status!="Yopildi").count(),
      "pending_users":User.query.filter_by(role="user",approved=False).count()}
    return render_template("dashboard.html",stats=stats,page="dashboard",
      tickets=Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all())

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("full_name","").strip()
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        if len(name)<3 or len(username)<3 or len(password)<8:
            flash("Ism/login kamida 3 belgi, parol kamida 8 belgidan iborat bo‘lsin.","error")
        elif User.query.filter_by(username=username).first():
            flash("Bu login band.","error")
        else:
            u=User(full_name=name,username=username,role="user",approved=False)
            u.set_password(password); db.session.add(u); db.session.commit()
            flash("So‘rovingiz adminga yuborildi. Tasdiqlanishini kuting.","success")
            return redirect(url_for("login"))
    return render_template("auth.html",mode="register",page="")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=User.query.filter_by(username=request.form.get("username","").strip().lower()).first()
        if not u or not u.check_password(request.form.get("password","")):
            flash("Login yoki parol noto‘g‘ri.","error")
        else:
            session.clear(); session["user_id"]=u.id
            if u.role!="admin" and not u.approved: return redirect(url_for("pending"))
            return redirect(url_for("home") if u.role=="admin" else url_for("userfeed"))
    return render_template("auth.html",mode="login",page="")

@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.get("/pending")
def pending():
    u=db.session.get(User,session.get("user_id")) if session.get("user_id") else None
    if not u: return redirect(url_for("login"))
    if u.role=="admin" or u.approved: return redirect(url_for("home") if u.role=="admin" else url_for("userfeed"))
    return render_template("pending.html",page="")

@app.route("/admin/users")
@admin_only
def users():
    return render_template("users.html",users=User.query.order_by(User.created_at.desc()).all(),page="users")

@app.post("/admin/users/<int:uid>/approve")
@admin_only
def approve(uid):
    u=db.get_or_404(User,uid)
    if u.role!="admin": u.approved=True; db.session.commit(); flash("Foydalanuvchi tasdiqlandi.","success")
    return redirect(url_for("users"))

@app.post("/admin/users/<int:uid>/delete")
@admin_only
def delete_user(uid):
    u=db.get_or_404(User,uid)
    if u.role!="admin": db.session.delete(u); db.session.commit(); flash("Foydalanuvchi o‘chirildi.","success")
    return redirect(url_for("users"))

@app.route("/userfeed",methods=["GET","POST"])
@signed_in
def userfeed():
    u=db.session.get(User,session["user_id"])
    if u.role=="admin": return redirect(url_for("home"))
    if request.method=="POST":
        title=request.form.get("title","").strip(); body=request.form.get("body","").strip()
        if title and body:
            db.session.add(Ticket(teacher=u.full_name,title=title,description=body,
              room=request.form.get("room","").strip() or None,
              priority=request.form.get("priority","O‘rta")))
            db.session.commit(); flash("Murojaat yuborildi.","success")
        else: flash("Mavzu va xabarni kiriting.","error")
        return redirect(url_for("userfeed"))
    # Tasdiqlangan foydalanuvchiga faqat o‘ziga mos keladigan jurnal baholarini ko‘rsatamiz.
    # O‘quvchi nomi ro‘yxatdan o‘tishdagi to‘liq ism bilan mos bo‘lishi kerak.
    student=Student.query.filter(db.func.lower(Student.name)==u.full_name.lower()).first()
    grades=[]
    if student:
        rows=(db.session.query(JournalEntry, Lesson)
              .join(Lesson, JournalEntry.lesson_id==Lesson.id)
              .filter(JournalEntry.student_id==student.id)
              .order_by(Lesson.date.desc()).all())
        grades=[{"entry":entry,"lesson":lesson} for entry,lesson in rows]
    return render_template("userfeed.html",
        tickets=Ticket.query.filter_by(teacher=u.full_name).order_by(Ticket.created_at.desc()).all(),
        grades=grades, student=student, page="userfeed")

@app.route("/students",methods=["GET","POST"])
@admin_only
def students():
    if request.method=="POST":
        n=request.form.get("name","").strip(); c=request.form.get("class_name","").strip()
        if n and c:
            db.session.add(Student(name=n,class_name=c,group_name=request.form.get("group_name","").strip() or "Asosiy")); db.session.commit()
            flash("O‘quvchi qo‘shildi.","success")
        else: flash("Ism va sinfni kiriting.","error")
        return redirect(url_for("students"))
    return render_template("students.html",students=Student.query.order_by(Student.class_name,Student.name).all(),page="students")

@app.post("/students/<int:sid>/delete")
@admin_only
def remove_student(sid):
    s=db.get_or_404(Student,sid); JournalEntry.query.filter_by(student_id=s.id).delete(); db.session.delete(s); db.session.commit()
    flash("O‘quvchi o‘chirildi.","success"); return redirect(url_for("students"))

@app.route("/lessons",methods=["GET","POST"])
@admin_only
def lessons():
    if request.method=="POST":
        try:
            db.session.add(Lesson(date=date.fromisoformat(request.form["lesson_date"]),topic=request.form["topic"].strip(),
              class_name=request.form["class_name"].strip(),quarter=request.form.get("quarter","1-chorak"),
              lesson_type=request.form.get("lesson_type","Amaliy"))); db.session.commit(); flash("Dars qo‘shildi.","success")
        except (ValueError,KeyError): flash("Sana, sinf va mavzuni to‘g‘ri kiriting.","error")
        return redirect(url_for("lessons"))
    ls=Lesson.query.order_by(Lesson.date.desc()).all(); ss=Student.query.order_by(Student.class_name,Student.name).all()
    es={(e.lesson_id,e.student_id):e for e in JournalEntry.query.all()}
    return render_template("lessons.html",lessons=ls,students=ss,entries=es,today=date.today().isoformat(),page="lessons")

@app.post("/lessons/<int:lid>/entry")
@admin_only
def entry(lid):
    lesson=db.get_or_404(Lesson,lid); student=db.get_or_404(Student,request.form.get("student_id",type=int))
    att=request.form.get("attendance",""); grade=request.form.get("grade","")
    if att not in ("","+","q","s"): att=""
    e=JournalEntry.query.filter_by(lesson_id=lesson.id,student_id=student.id).first()
    if not e: e=JournalEntry(lesson_id=lesson.id,student_id=student.id); db.session.add(e)
    e.attendance=att or None; e.grade=int(grade) if grade in ("1","2","3","4","5") else None
    db.session.commit(); flash("Jurnal saqlandi.","success"); return redirect(url_for("lessons"))

@app.route("/inventory",methods=["GET","POST"])
@admin_only
def inventory():
    if request.method=="POST":
        name=request.form.get("name","").strip(); serial=request.form.get("serial_number","").strip() or None
        if not name: flash("Jihoz nomini kiriting.","error")
        elif serial and Equipment.query.filter_by(serial_number=serial).first(): flash("Seriya raqami mavjud.","error")
        else:
            db.session.add(Equipment(name=name,category=request.form.get("category","Kompyuter"),serial_number=serial,
              room=request.form.get("room","").strip() or None,status=request.form.get("status","Soz"))); db.session.commit(); flash("Jihoz saqlandi.","success")
        return redirect(url_for("inventory"))
    return render_template("inventory.html",equipment=Equipment.query.order_by(Equipment.name).all(),page="inventory")

@app.post("/inventory/<int:iid>/update")
@admin_only
def update_inventory(iid):
    i=db.get_or_404(Equipment,iid); s=request.form.get("status","Soz")
    if s in ("Soz","Ta'mirda","Buzuq"): i.status=s; db.session.commit()
    return redirect(url_for("inventory"))

@app.post("/inventory/<int:iid>/delete")
@admin_only
def remove_inventory(iid):
    db.session.delete(db.get_or_404(Equipment,iid)); db.session.commit(); return redirect(url_for("inventory"))

@app.route("/tickets",methods=["GET","POST"])
@admin_only
def tickets():
    if request.method=="POST":
        db.session.add(Ticket(teacher=request.form.get("teacher","").strip(),title=request.form.get("title","").strip(),
          description=request.form.get("description","").strip(),room=request.form.get("room","").strip() or None,
          priority=request.form.get("priority","O‘rta"))); db.session.commit(); return redirect(url_for("tickets"))
    return render_template("tickets.html",tickets=Ticket.query.order_by(Ticket.created_at.desc()).all(),page="tickets")

@app.post("/tickets/<int:tid>/status")
@admin_only
def ticket_status(tid):
    t=db.get_or_404(Ticket,tid); s=request.form.get("status","Yangi")
    if s in ("Yangi","Jarayonda","Yopildi"): t.status=s; db.session.commit()
    return redirect(url_for("tickets"))

@app.errorhandler(403)
def forbidden(e): return render_template("error.html",code=403,page=""),403
@app.errorhandler(404)
def not_found(e): return render_template("error.html",code=404,page=""),404

if __name__=="__main__": app.run(debug=True)
