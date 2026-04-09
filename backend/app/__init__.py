from datetime import datetime, timedelta

from flask import Flask, jsonify

from .auth import auth_bp
from .celery_utils import create_celery
from .config import Config
from .extensions import cache, cors, db, jwt, migrate
from .models import User
from .routes.admin import admin_bp
from .routes.company import company_bp
from .routes.student import student_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure API processes dispatch shared Celery tasks using this configured app.
    celery_app = create_celery(app)
    celery_app.set_default()
    app.extensions["celery"] = celery_app

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        admin = User.query.filter_by(role="ADMIN").first()
        if not admin:
            admin = User(
                email=app.config["ADMIN_EMAIL"],
                role="ADMIN",
                full_name="Institute Admin",
            )
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)
            db.session.commit()
            print("Admin created")
        else:
            print("Admin already exists")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        from .models import Application, ApplicationStatusHistory, CompanyProfile, PlacementDrive, StudentProfile, User

        db.create_all()

        admin = User.query.filter_by(role="ADMIN").first()
        if not admin:
            admin = User(
                email=app.config["ADMIN_EMAIL"],
                role="ADMIN",
                full_name="Institute Admin",
            )
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)
        current_grad_year = datetime.utcnow().year + 1

        def ensure_user(email, role, full_name, password):
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(email=email, role=role, full_name=full_name)
                db.session.add(user)
            user.role = role
            user.full_name = full_name
            user.is_active = True
            user.is_blacklisted = False
            user.set_password(password)
            db.session.flush()
            return user

        company_specs = [
            {
                "slug": "hsbc",
                "company_name": "HSBC",
                "hr_contact": "hr@hsbc.demo",
                "website": "https://www.hsbc.com",
                "approval_status": "APPROVED",
            },
            {
                "slug": "samsung",
                "company_name": "Samsung",
                "hr_contact": "hr@samsung.demo",
                "website": "https://www.samsung.com",
                "approval_status": "APPROVED",
            },
            {
                "slug": "cisco",
                "company_name": "Cisco",
                "hr_contact": "hr@cisco.demo",
                "website": "https://www.cisco.com",
                "approval_status": "APPROVED",
            },
            {
                "slug": "nutanix",
                "company_name": "Nutanix",
                "hr_contact": "hr@nutanix.demo",
                "website": "https://www.nutanix.com",
                "approval_status": "APPROVED",
            },
            {
                "slug": "arista",
                "company_name": "Arista",
                "hr_contact": "hr@arista.demo",
                "website": "https://www.arista.com",
                "approval_status": "APPROVED",
            },
        ]

        student_specs = [
            {"email": "student1.demo@college.local", "name": "Student One", "branch": "CSE", "cgpa": 8.9},
            {"email": "student2.demo@college.local", "name": "Student Two", "branch": "CSE", "cgpa": 8.7},
            {"email": "student3.demo@college.local", "name": "Student Three", "branch": "CSE", "cgpa": 8.1},
            {"email": "student4.demo@college.local", "name": "Student Four", "branch": "CSE", "cgpa": 8.6},
            {"email": "student5.demo@college.local", "name": "Student Five", "branch": "CSE", "cgpa": 8.3},
            {"email": "student6.demo@college.local", "name": "Student Six", "branch": "CSE", "cgpa": 8.4},
            {"email": "student7.demo@college.local", "name": "Student Seven", "branch": "CSE", "cgpa": 7.9},
            {"email": "student8.demo@college.local", "name": "Student Eight", "branch": "CSE", "cgpa": 8.0},
            {"email": "student9.demo@college.local", "name": "Student Nine", "branch": "CSE", "cgpa": 8.2},
            {"email": "student10.demo@college.local", "name": "Student Ten", "branch": "CSE", "cgpa": 8.5},
        ]

        company_profiles_by_slug = {}
        for spec in company_specs:
            recruiter = ensure_user(
                email=f"recruiter.{spec['slug']}@corp.local",
                role="COMPANY",
                full_name=f"{spec['company_name']} Recruiter",
                password="company123",
            )
            company_profile = CompanyProfile.query.filter_by(user_id=recruiter.id).first()
            if not company_profile:
                company_profile = CompanyProfile(user_id=recruiter.id)
                db.session.add(company_profile)
            company_profile.company_name = spec["company_name"]
            company_profile.hr_contact = spec["hr_contact"]
            company_profile.website = spec["website"]
            company_profile.approval_status = spec["approval_status"]
            company_profiles_by_slug[spec["slug"]] = company_profile

        student_profiles_by_email = {}
        for spec in student_specs:
            student_user = ensure_user(
                email=spec["email"],
                role="STUDENT",
                full_name=spec["name"],
                password="student123",
            )
            student_profile = StudentProfile.query.filter_by(user_id=student_user.id).first()
            if not student_profile:
                student_profile = StudentProfile(user_id=student_user.id)
                db.session.add(student_profile)
            student_profile.branch = spec["branch"]
            student_profile.cgpa = spec["cgpa"]
            student_profile.graduation_year = current_grad_year
            student_profile.resume_url = f"https://example.com/resume-{student_user.id}.pdf"
            student_profiles_by_email[spec["email"]] = student_profile

        db.session.flush()

        now = datetime.utcnow()
        drive_specs = [
            {
                "slug": "hsbc",
                "job_title": "HSBC Graduate Analyst",
                "status": "CLOSED",
                "deadline": now - timedelta(days=10),
            },
            {
                "slug": "samsung",
                "job_title": "Samsung Software Engineer",
                "status": "CLOSED",
                "deadline": now - timedelta(days=8),
            },
            {
                "slug": "cisco",
                "job_title": "Cisco Associate Engineer",
                "status": "CLOSED",
                "deadline": now - timedelta(days=6),
            },
            {
                "slug": "nutanix",
                "job_title": "Nutanix MTS Intern",
                "status": "PENDING",
                "deadline": now + timedelta(days=12),
            },
            {
                "slug": "arista",
                "job_title": "Arista Network Engineer",
                "status": "PENDING",
                "deadline": now + timedelta(days=15),
            },
        ]

        drives_by_slug = {}
        for spec in drive_specs:
            company_profile = company_profiles_by_slug[spec["slug"]]
            drive = PlacementDrive.query.filter_by(company_id=company_profile.id, job_title=spec["job_title"]).first()
            if not drive:
                drive = PlacementDrive(company_id=company_profile.id, job_title=spec["job_title"])
                db.session.add(drive)
            drive.job_description = f"{company_profile.company_name} campus hiring program."
            drive.eligible_branch = "CSE"
            drive.min_cgpa = 7.0
            drive.eligible_year = current_grad_year
            drive.application_deadline = spec["deadline"]
            drive.status = spec["status"]
            drives_by_slug[spec["slug"]] = drive

        db.session.flush()

        seeded_applications = [
            ("student1.demo@college.local", "hsbc", "SELECTED"),
            ("student2.demo@college.local", "hsbc", "REJECTED"),
            ("student3.demo@college.local", "hsbc", "APPLIED"),
            ("student4.demo@college.local", "samsung", "SELECTED"),
            ("student5.demo@college.local", "samsung", "SHORTLISTED"),
            ("student6.demo@college.local", "samsung", "REJECTED"),
            ("student7.demo@college.local", "cisco", "SELECTED"),
            ("student8.demo@college.local", "cisco", "SHORTLISTED"),
            ("student9.demo@college.local", "cisco", "REJECTED"),
            ("student10.demo@college.local", "cisco", "APPLIED"),
        ]

        for idx, (student_email, company_slug, final_status) in enumerate(seeded_applications, start=1):
            student_profile = student_profiles_by_email[student_email]
            drive = drives_by_slug[company_slug]
            application = Application.query.filter_by(student_id=student_profile.id, drive_id=drive.id).first()
            if not application:
                application = Application(student_id=student_profile.id, drive_id=drive.id)
                db.session.add(application)
            application.application_date = now - timedelta(days=20 - idx)
            application.status = final_status
            db.session.flush()

            ApplicationStatusHistory.query.filter_by(application_id=application.id).delete()
            db.session.add(
                ApplicationStatusHistory(
                    application_id=application.id,
                    from_status=None,
                    to_status="APPLIED",
                    changed_by_user_id=student_profile.user_id,
                    changed_at=application.application_date,
                )
            )
            if final_status != "APPLIED":
                db.session.add(
                    ApplicationStatusHistory(
                        application_id=application.id,
                        from_status="APPLIED",
                        to_status=final_status,
                        changed_by_user_id=drive.company.user_id,
                        changed_at=application.application_date + timedelta(days=2),
                    )
                )

        db.session.commit()
        print("Demo data seeded successfully")
        print("Admin: admin@institute.local / <ADMIN_PASSWORD from env>")
        print("Company login password for all seeded recruiters: company123")
        print("Student login password for all seeded students: student123")
        print("Closed drives with hiring completed: HSBC, Samsung, Cisco")
        print("Pending drive approval requests: Nutanix, Arista")

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(int(identity))

    return app
