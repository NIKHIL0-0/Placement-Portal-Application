from pathlib import Path
from uuid import uuid4

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from ..decorators import role_required
from ..extensions import cache, db
from ..models import Application, ApplicationStatusHistory, AsyncTaskLog, CompanyProfile, PlacementDrive, StudentProfile, User
from ..tasks import export_student_applications_task


student_bp = Blueprint("student", __name__, url_prefix="/api/student")


def _safe_cache_clear():
    try:
        cache.clear()
    except Exception:
        # Do not fail profile update if cache backend is unavailable.
        pass


def _resume_upload_dir() -> Path:
    configured = current_app.config.get("UPLOAD_FOLDER", "uploads/resumes")
    path = Path(configured)
    if not path.is_absolute():
        path = Path(current_app.root_path).parent / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_allowed_resume_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_RESUME_EXTENSIONS", {"pdf", "doc", "docx"})


@student_bp.get("/dashboard")
@role_required("STUDENT")
def dashboard():
    user_id = int(get_jwt_identity())
    student = StudentProfile.query.filter_by(user_id=user_id).first_or_404()
    branch = request.args.get("branch", "")
    q = request.args.get("q", "").strip()
    cache_key = f"student_dashboard:{user_id}:{branch}:{q}"

    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    drives = PlacementDrive.query.filter_by(status="APPROVED")
    if branch:
        drives = drives.filter_by(eligible_branch=branch)
    if q:
        like = f"%{q}%"
        drives = drives.filter(PlacementDrive.job_title.ilike(like))

    approved_drives = drives.order_by(PlacementDrive.application_deadline.asc()).all()

    payload = {
        "student": {
            "name": student.user.full_name,
            "branch": student.branch,
            "cgpa": student.cgpa,
            "graduation_year": student.graduation_year,
            "resume_url": student.resume_url,
        },
        "approved_drives": [
            {
                "id": d.id,
                "company": d.company.company_name,
                "job_title": d.job_title,
                "eligible_branch": d.eligible_branch,
                "min_cgpa": d.min_cgpa,
                "eligible_year": d.eligible_year,
                "deadline": d.application_deadline.isoformat(),
            }
            for d in approved_drives
        ],
    }

    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass

    return jsonify(payload)


@student_bp.put("/profile")
@role_required("STUDENT")
def update_profile():
    user_id = int(get_jwt_identity())
    student = StudentProfile.query.filter_by(user_id=user_id).first_or_404()
    data = request.get_json() or {}

    if "branch" in data:
        branch = str(data["branch"]).strip()
        if not branch:
            return jsonify({"message": "Branch cannot be empty"}), 400
        student.branch = branch
    if "cgpa" in data:
        cgpa = float(data["cgpa"])
        if cgpa < 0 or cgpa > 10:
            return jsonify({"message": "CGPA must be between 0 and 10"}), 400
        student.cgpa = cgpa
    if "graduation_year" in data:
        graduation_year = int(data["graduation_year"])
        if graduation_year < 2020 or graduation_year > 2100:
            return jsonify({"message": "Graduation year must be between 2020 and 2100"}), 400
        student.graduation_year = graduation_year
    if "resume_url" in data:
        student.resume_url = str(data["resume_url"]).strip() or None

    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Profile updated"})


@student_bp.post("/profile/resume")
@role_required("STUDENT")
def upload_resume():
    user_id = int(get_jwt_identity())
    student = StudentProfile.query.filter_by(user_id=user_id).first_or_404()

    if "resume" not in request.files:
        return jsonify({"message": "resume file is required"}), 400

    resume_file = request.files["resume"]
    file_name = resume_file.filename or ""
    if file_name == "":
        return jsonify({"message": "Please choose a resume file"}), 400
    if not _is_allowed_resume_file(file_name):
        return jsonify({"message": "Allowed resume formats: pdf, doc, docx"}), 400

    safe_name = secure_filename(file_name)
    ext = safe_name.rsplit(".", 1)[1].lower()
    stored_name = f"student_{student.id}_{uuid4().hex}.{ext}"

    upload_dir = _resume_upload_dir()
    file_path = upload_dir / stored_name
    resume_file.save(file_path)

    student.resume_url = f"/api/student/resume/{stored_name}"
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Resume uploaded successfully", "resume_url": student.resume_url})


@student_bp.get("/resume/<path:filename>")
@role_required("STUDENT", "ADMIN", "COMPANY")
def serve_resume(filename):
    upload_dir = _resume_upload_dir()
    safe_name = secure_filename(filename)
    file_path = upload_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"message": "Resume not found"}), 404
    return send_file(file_path)


@student_bp.post("/drives/<int:drive_id>/apply")
@role_required("STUDENT")
def apply_drive(drive_id):
    user_id = int(get_jwt_identity())
    student = StudentProfile.query.filter_by(user_id=user_id).first_or_404()
    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.status != "APPROVED":
        return jsonify({"message": "Drive is not open for applications"}), 400

    if drive.application_deadline < datetime.utcnow():
        return jsonify({"message": "Application deadline has passed"}), 400

    if student.branch != drive.eligible_branch:
        return jsonify({"message": "Not eligible by branch"}), 400

    if student.cgpa < drive.min_cgpa:
        return jsonify({"message": "Not eligible by CGPA"}), 400

    if student.graduation_year != drive.eligible_year:
        return jsonify({"message": "Not eligible by graduation year"}), 400

    existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing:
        return jsonify({"message": "Already applied to this drive"}), 409

    application = Application(student_id=student.id, drive_id=drive.id)
    db.session.add(application)
    db.session.flush()
    db.session.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=None,
            to_status="APPLIED",
            changed_by_user_id=user_id,
        )
    )
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Application submitted"}), 201


@student_bp.get("/applications")
@role_required("STUDENT")
def list_applications():
    user_id = int(get_jwt_identity())
    student = StudentProfile.query.filter_by(user_id=user_id).first_or_404()
    cache_key = f"student_applications:{student.id}"

    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    apps = Application.query.filter_by(student_id=student.id).order_by(Application.application_date.desc()).all()
    payload = [
        {
            "id": app.id,
            "drive_id": app.drive_id,
            "company": app.drive.company.company_name,
            "drive_title": app.drive.job_title,
            "status": app.status,
            "applied_at": app.application_date.isoformat(),
            "status_history": (
                [
                    {
                        "from_status": h.from_status,
                        "to_status": h.to_status,
                        "changed_by_user_id": h.changed_by_user_id,
                        "changed_at": h.changed_at.isoformat(),
                    }
                    for h in app.status_history
                ]
                if app.status_history
                else [
                    {
                        "from_status": None,
                        "to_status": "APPLIED",
                        "changed_by_user_id": app.student.user_id,
                        "changed_at": app.application_date.isoformat(),
                    }
                ]
            ),
        }
        for app in apps
    ]

    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass

    return jsonify(payload)


@student_bp.post("/applications/export")
@role_required("STUDENT")
def export_applications():
    user_id = int(get_jwt_identity())
    task_id = uuid4().hex
    log = AsyncTaskLog(user_id=user_id, task_id=task_id, task_type="EXPORT_CSV", status="PENDING")
    db.session.add(log)
    db.session.commit()

    try:
        export_student_applications_task.apply_async(args=[user_id], task_id=task_id)
    except Exception:
        db.session.delete(log)
        db.session.commit()
        return jsonify({"message": "Export queue is currently unavailable"}), 503

    return jsonify({"message": "Export started", "task_id": task_id}), 202


@student_bp.get("/tasks/<task_id>")
@role_required("STUDENT")
def task_status(task_id):
    user_id = int(get_jwt_identity())
    log = AsyncTaskLog.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    return jsonify({"task_id": log.task_id, "status": log.status, "result_path": log.result_path})


@student_bp.get("/companies")
@role_required("STUDENT")
def search_companies():
    query = request.args.get("q", "").strip()
    cache_key = f"student_companies:{query}"

    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    companies_query = CompanyProfile.query.join(User).filter(CompanyProfile.approval_status == "APPROVED")
    if query:
        like = f"%{query}%"
        companies_query = companies_query.filter(
            or_(
                CompanyProfile.company_name.ilike(like),
                CompanyProfile.hr_contact.ilike(like),
                User.email.ilike(like),
            )
        )

    companies = companies_query.order_by(CompanyProfile.company_name.asc()).all()
    payload = [
        {
            "id": c.id,
            "company_name": c.company_name,
            "hr_contact": c.hr_contact,
            "website": c.website,
        }
        for c in companies
    ]

    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass

    return jsonify(payload)


@student_bp.get("/tasks/<task_id>/download")
@role_required("STUDENT")
def download_export(task_id):
    user_id = int(get_jwt_identity())
    log = AsyncTaskLog.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    if log.status != "COMPLETED" or not log.result_path:
        return jsonify({"message": "Export is not ready yet"}), 400

    file_path = Path(log.result_path)
    if not file_path.is_absolute():
        file_path = Path(current_app.root_path).parent / file_path
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"message": "Export file not found"}), 404

    return send_file(file_path, as_attachment=True, download_name=file_path.name, mimetype="text/csv")
