from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company_profile = db.relationship("CompanyProfile", back_populates="user", uselist=False)
    student_profile = db.relationship("StudentProfile", back_populates="user", uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class CompanyProfile(db.Model):
    __tablename__ = "company_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    company_name = db.Column(db.String(150), nullable=False, index=True)
    hr_contact = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    approval_status = db.Column(db.String(20), default="PENDING", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="company_profile")
    drives = db.relationship("PlacementDrive", back_populates="company", cascade="all, delete-orphan")


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    branch = db.Column(db.String(80), nullable=False, index=True)
    cgpa = db.Column(db.Float, nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False, index=True)
    resume_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="student_profile")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")


class PlacementDrive(db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company_profiles.id"), nullable=False)
    job_title = db.Column(db.String(120), nullable=False, index=True)
    job_description = db.Column(db.Text, nullable=False)
    eligible_branch = db.Column(db.String(80), nullable=False)
    min_cgpa = db.Column(db.Float, nullable=False, default=0.0)
    eligible_year = db.Column(db.Integer, nullable=False)
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("CompanyProfile", back_populates="drives")
    applications = db.relationship("Application", back_populates="drive", cascade="all, delete-orphan")


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id"), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default="APPLIED", nullable=False, index=True)

    student = db.relationship("StudentProfile", back_populates="applications")
    drive = db.relationship("PlacementDrive", back_populates="applications")
    interview = db.relationship("InterviewSchedule", back_populates="application", uselist=False)
    status_history = db.relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at.asc()",
    )

    __table_args__ = (
        db.UniqueConstraint("student_id", "drive_id", name="uq_student_drive_application"),
    )


class InterviewSchedule(db.Model):
    __tablename__ = "interview_schedules"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, unique=True)
    interview_at = db.Column(db.DateTime, nullable=False)
    mode = db.Column(db.String(30), nullable=False, default="ONLINE")
    meeting_link = db.Column(db.String(255), nullable=True)

    application = db.relationship("Application", back_populates="interview")


class AsyncTaskLog(db.Model):
    __tablename__ = "async_task_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    task_id = db.Column(db.String(100), nullable=False, unique=True)
    task_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False)
    result_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ApplicationStatusHistory(db.Model):
    __tablename__ = "application_status_history"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False, index=True)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    application = db.relationship("Application", back_populates="status_history")
