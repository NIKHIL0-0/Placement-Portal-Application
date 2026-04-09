from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..decorators import role_required
from ..extensions import cache, db
from ..models import Application, ApplicationStatusHistory, CompanyProfile, InterviewSchedule, PlacementDrive


company_bp = Blueprint("company", __name__, url_prefix="/api/company")


def _safe_cache_clear():
    try:
        cache.clear()
    except Exception:
        # Do not fail successful DB writes if cache backend is unavailable.
        pass


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


@company_bp.get("/dashboard")
@role_required("COMPANY")
def dashboard():
    user_id = int(get_jwt_identity())
    company = CompanyProfile.query.filter_by(user_id=user_id).first_or_404()
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return jsonify(
        {
            "company": {
                "id": company.id,
                "name": company.company_name,
                "approval_status": company.approval_status,
                "website": company.website,
            },
            "drives": [
                {
                    "id": d.id,
                    "job_title": d.job_title,
                    "status": d.status,
                    "deadline": d.application_deadline.isoformat(),
                    "applicants": len(d.applications),
                }
                for d in drives
            ],
        }
    )


@company_bp.post("/drives")
@role_required("COMPANY")
def create_drive():
    user_id = int(get_jwt_identity())
    company = CompanyProfile.query.filter_by(user_id=user_id).first_or_404()
    if company.approval_status != "APPROVED":
        return jsonify({"message": "Company not approved"}), 403

    data = request.get_json() or {}
    required = ["job_title", "job_description", "eligible_branch", "min_cgpa", "eligible_year", "application_deadline"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"message": "Missing fields", "fields": missing}), 400

    try:
        min_cgpa = float(data["min_cgpa"])
    except (TypeError, ValueError):
        return jsonify({"message": "min_cgpa must be a number"}), 400
    if min_cgpa < 0 or min_cgpa > 10:
        return jsonify({"message": "min_cgpa must be between 0 and 10"}), 400

    try:
        eligible_year = int(data["eligible_year"])
    except (TypeError, ValueError):
        return jsonify({"message": "eligible_year must be a valid year"}), 400
    if eligible_year < 2020 or eligible_year > 2100:
        return jsonify({"message": "eligible_year must be between 2020 and 2100"}), 400

    try:
        application_deadline = _to_utc_naive(datetime.fromisoformat(data["application_deadline"]))
    except (TypeError, ValueError):
        return jsonify({"message": "application_deadline must be a valid ISO datetime"}), 400
    if application_deadline <= datetime.utcnow():
        return jsonify({"message": "application_deadline must be in the future"}), 400

    drive = PlacementDrive(
        company_id=company.id,
        job_title=data["job_title"].strip(),
        job_description=data["job_description"].strip(),
        eligible_branch=data["eligible_branch"].strip(),
        min_cgpa=min_cgpa,
        eligible_year=eligible_year,
        application_deadline=application_deadline,
        status="PENDING",
    )

    db.session.add(drive)
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Drive created and pending admin approval", "drive_id": drive.id}), 201


@company_bp.get("/drives/<int:drive_id>/applications")
@role_required("COMPANY")
def drive_applications(drive_id):
    user_id = int(get_jwt_identity())
    company = CompanyProfile.query.filter_by(user_id=user_id).first_or_404()
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    return jsonify(
        [
            {
                "application_id": app.id,
                "student_name": app.student.user.full_name,
                "student_email": app.student.user.email,
                "branch": app.student.branch,
                "cgpa": app.student.cgpa,
                "status": app.status,
                "applied_at": app.application_date.isoformat(),
                "interview": app.interview.interview_at.isoformat() if app.interview else None,
            }
            for app in drive.applications
        ]
    )


@company_bp.put("/applications/<int:application_id>/status")
@role_required("COMPANY")
def update_application_status(application_id):
    user_id = int(get_jwt_identity())
    company = CompanyProfile.query.filter_by(user_id=user_id).first_or_404()
    app = Application.query.get_or_404(application_id)
    if app.drive.company_id != company.id:
        return jsonify({"message": "Forbidden"}), 403

    data = request.get_json() or {}
    status = data.get("status", "").upper()
    if status not in {"SHORTLISTED", "SELECTED", "REJECTED", "APPLIED"}:
        return jsonify({"message": "Invalid status"}), 400

    allowed_transitions = {
        "APPLIED": {"SHORTLISTED", "REJECTED"},
        "SHORTLISTED": {"SELECTED", "REJECTED"},
        "SELECTED": set(),
        "REJECTED": set(),
    }
    if status == app.status:
        return jsonify({"message": "Application already in requested status"}), 400
    if status not in allowed_transitions.get(app.status, set()):
        return jsonify({"message": f"Invalid status transition from {app.status} to {status}"}), 400

    previous_status = app.status
    app.status = status
    db.session.add(
        ApplicationStatusHistory(
            application_id=app.id,
            from_status=previous_status,
            to_status=status,
            changed_by_user_id=user_id,
        )
    )
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Application status updated"})


@company_bp.post("/applications/<int:application_id>/interview")
@role_required("COMPANY")
def schedule_interview(application_id):
    user_id = int(get_jwt_identity())
    company = CompanyProfile.query.filter_by(user_id=user_id).first_or_404()
    app = Application.query.get_or_404(application_id)
    if app.drive.company_id != company.id:
        return jsonify({"message": "Forbidden"}), 403

    data = request.get_json() or {}
    if not data.get("interview_at"):
        return jsonify({"message": "interview_at required"}), 400

    try:
        interview_at = _to_utc_naive(datetime.fromisoformat(data["interview_at"]))
    except (TypeError, ValueError):
        return jsonify({"message": "interview_at must be a valid ISO datetime"}), 400

    if interview_at <= datetime.utcnow():
        return jsonify({"message": "interview_at must be in the future"}), 400

    mode = str(data.get("mode", "ONLINE")).upper()
    if mode not in {"ONLINE", "OFFLINE"}:
        return jsonify({"message": "mode must be ONLINE or OFFLINE"}), 400

    interview = app.interview
    if not interview:
        interview = InterviewSchedule(application=app, interview_at=interview_at)
    else:
        interview.interview_at = interview_at
    interview.mode = mode
    interview.meeting_link = data.get("meeting_link")

    db.session.add(interview)
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Interview schedule updated"})
