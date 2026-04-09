from datetime import datetime, timedelta, timezone
from io import BytesIO

from app import create_app
from app.extensions import db
from app.models import Application, CompanyProfile, PlacementDrive, StudentProfile, User


def _create_user(email, password, role, full_name):
    existing = User.query.filter_by(email=email).first()
    if existing:
        existing.role = role
        existing.full_name = full_name
        existing.is_active = True
        existing.is_blacklisted = False
        return existing
    user = User(email=email, role=role, full_name=full_name)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def run_smoke_test():
    app = create_app()
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
        if not admin:
            admin = User(email=app.config["ADMIN_EMAIL"], role="ADMIN", full_name="Institute Admin")
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)

        company_user = _create_user("smoke.company@local.test", "company123", "COMPANY", "Smoke Company User")
        if not company_user.company_profile:
            db.session.add(
                CompanyProfile(
                    user_id=company_user.id,
                    company_name="Smoke Corp",
                    hr_contact="hr@smoke.test",
                    website="https://smoke.test",
                    approval_status="APPROVED",
                )
            )

        student_user = _create_user("smoke.student@local.test", "student123", "STUDENT", "Smoke Student")
        if not student_user.student_profile:
            db.session.add(
                StudentProfile(
                    user_id=student_user.id,
                    branch="CSE",
                    cgpa=8.0,
                    graduation_year=datetime.now(timezone.utc).year + 1,
                    resume_url="https://smoke.test/resume.pdf",
                )
            )

        db.session.commit()

    client = app.test_client()

    admin_login = client.post(
        "/api/auth/login",
        json={"email": app.config["ADMIN_EMAIL"], "password": app.config["ADMIN_PASSWORD"]},
    )
    assert admin_login.status_code == 200, admin_login.get_json()
    admin_token = admin_login.get_json()["access_token"]

    company_login = client.post(
        "/api/auth/login",
        json={"email": "smoke.company@local.test", "password": "company123"},
    )
    assert company_login.status_code == 200, company_login.get_json()
    company_token = company_login.get_json()["access_token"]

    drive_create = client.post(
        "/api/company/drives",
        headers={"Authorization": f"Bearer {company_token}"},
        json={
            "job_title": "Smoke Engineer",
            "job_description": "Smoke test drive",
            "eligible_branch": "CSE",
            "min_cgpa": 7,
            "eligible_year": datetime.now(timezone.utc).year + 1,
            "application_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
    )
    assert drive_create.status_code == 201, drive_create.get_json()
    drive_id = drive_create.get_json()["drive_id"]

    approve_drive = client.put(
        f"/api/admin/drives/{drive_id}/approval",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "APPROVED"},
    )
    assert approve_drive.status_code == 200, approve_drive.get_json()

    student_login = client.post(
        "/api/auth/login",
        json={"email": "smoke.student@local.test", "password": "student123"},
    )
    assert student_login.status_code == 200, student_login.get_json()
    student_token = student_login.get_json()["access_token"]

    apply_drive = client.post(
        f"/api/student/drives/{drive_id}/apply",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert apply_drive.status_code in (200, 201), apply_drive.get_json()

    duplicate_apply = client.post(
        f"/api/student/drives/{drive_id}/apply",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert duplicate_apply.status_code == 409, duplicate_apply.get_json()

    with app.app_context():
        company_profile = CompanyProfile.query.join(User).filter(User.email == "smoke.company@local.test").first()
        student_profile = StudentProfile.query.join(User).filter(User.email == "smoke.student@local.test").first()
        app_row = Application.query.filter_by(student_id=student_profile.id, drive_id=drive_id).first()
        assert app_row is not None

    shortlist = client.put(
        f"/api/company/applications/{app_row.id}/status",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"status": "SHORTLISTED"},
    )
    assert shortlist.status_code == 200, shortlist.get_json()

    select = client.put(
        f"/api/company/applications/{app_row.id}/status",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"status": "SELECTED"},
    )
    assert select.status_code == 200, select.get_json()

    invalid_transition = client.put(
        f"/api/company/applications/{app_row.id}/status",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"status": "SHORTLISTED"},
    )
    assert invalid_transition.status_code == 400, invalid_transition.get_json()

    schedule_missing_datetime = client.post(
        f"/api/company/applications/{app_row.id}/interview",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"mode": "ONLINE", "meeting_link": "https://meet.example.com/abc"},
    )
    assert schedule_missing_datetime.status_code == 400, schedule_missing_datetime.get_json()

    schedule_interview = client.post(
        f"/api/company/applications/{app_row.id}/interview",
        headers={"Authorization": f"Bearer {company_token}"},
        json={
            "interview_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "mode": "ONLINE",
            "meeting_link": "https://meet.example.com/abc",
        },
    )
    assert schedule_interview.status_code == 200, schedule_interview.get_json()

    resume_upload = client.post(
        "/api/student/profile/resume",
        headers={"Authorization": f"Bearer {student_token}"},
        data={"resume": (BytesIO(b"%PDF-1.4\n%test resume"), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert resume_upload.status_code == 200, resume_upload.get_json()

    export_start = client.post(
        "/api/student/applications/export",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    if export_start.status_code == 202:
        task_id = export_start.get_json()["task_id"]

        export_status = client.get(
            f"/api/student/tasks/{task_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert export_status.status_code == 200, export_status.get_json()

        export_download = client.get(
            f"/api/student/tasks/{task_id}/download",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert export_download.status_code == 400, export_download.get_json()
    else:
        # Celery broker may not be running during smoke checks.
        assert export_start.status_code in (500, 503), export_start.get_json()

    print("Smoke test passed: auth, drive flow, validations, transitions, resume upload, export flow")


if __name__ == "__main__":
    run_smoke_test()
