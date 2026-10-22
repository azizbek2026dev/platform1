from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name=db.Column(db.String(160), nullable=False)
    password_hash=db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(20), nullable=False, default="user")
    approved=db.Column(db.Boolean, nullable=False, default=False)
    created_at=db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    def set_password(self, password): self.password_hash=generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(160), nullable=False)
    class_name=db.Column(db.String(30), nullable=False, index=True)
    group_name=db.Column(db.String(60), nullable=False, default="Asosiy")

class Lesson(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    date=db.Column(db.Date, nullable=False, index=True)
    topic=db.Column(db.String(240), nullable=False)
    class_name=db.Column(db.String(30), nullable=False)
    quarter=db.Column(db.String(20), nullable=False, default="1-chorak")
    lesson_type=db.Column(db.String(30), nullable=False, default="Amaliy")

class JournalEntry(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    lesson_id=db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    student_id=db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    attendance=db.Column(db.String(2))
    grade=db.Column(db.Integer)
    __table_args__=(db.UniqueConstraint("lesson_id","student_id",name="uq_lesson_student"),)

class Equipment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(160), nullable=False)
    category=db.Column(db.String(50), nullable=False, default="Kompyuter")
    serial_number=db.Column(db.String(100), unique=True)
    room=db.Column(db.String(60))
    status=db.Column(db.String(30), nullable=False, default="Soz")

class Ticket(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    teacher=db.Column(db.String(160), nullable=False)
    room=db.Column(db.String(60))
    title=db.Column(db.String(180), nullable=False)
    description=db.Column(db.Text, nullable=False)
    priority=db.Column(db.String(20), nullable=False, default="O‘rta")
    status=db.Column(db.String(30), nullable=False, default="Yangi")
    created_at=db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
