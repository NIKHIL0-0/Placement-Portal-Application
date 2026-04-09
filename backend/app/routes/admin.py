from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import desc, func, or_

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity

from ..decorators import role_required
from ..extensions import cache, db
from ..models import Application, AsyncTaskLog, CompanyProfile, PlacementDrive, StudentProfile, User


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _safe_cache_clear():
    try:
        cache.clear()
    except Exception:
        # Do not fail approval/status updates if cache backend is temporarily unavailable.
        pass


def _pagination_args():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    return page, per_page


def _paginated_response(pagination, items):
    return {
        "items": items,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }


def _parse_date_param(raw_value: str, field_name: str):
    if not raw_value:
        return None, f"{field_name} is required"
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d"), None
    except ValueError:
        return None, f"{field_name} must be in YYYY-MM-DD format"


@admin_bp.get("/dashboard")
@role_required("ADMIN")
def dashboard():
    cache_key = "admin_dashboard_counts"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        # Continue without cache if Redis is unavailable.
        pass

    payload = {
        "students": User.query.filter_by(role="STUDENT").count(),
        "companies": CompanyProfile.query.filter_by(approval_status="APPROVED").count(),
        "drives": PlacementDrive.query.filter(PlacementDrive.status.in_(["APPROVED", "CLOSED"])).count(),
        "applications": Application.query.count(),
    }

    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        # Do not fail response if cache write fails.
        pass

    return jsonify(payload)


@admin_bp.put("/companies/<int:company_id>/approval")
@role_required("ADMIN")
def update_company_approval(company_id):
    data = request.get_json() or {}
    status = data.get("status", "").upper()
    if status not in {"APPROVED", "REJECTED"}:
        return jsonify({"message": "Status must be APPROVED or REJECTED"}), 400

    company = CompanyProfile.query.get_or_404(company_id)
    company.approval_status = status
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Company approval updated"})


@admin_bp.put("/drives/<int:drive_id>/approval")
@role_required("ADMIN")
def update_drive_approval(drive_id):
    data = request.get_json() or {}
    status = data.get("status", "").upper()
    if status not in {"APPROVED", "REJECTED", "CLOSED"}:
        return jsonify({"message": "Invalid status"}), 400

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = status
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "Drive status updated"})


@admin_bp.get("/companies")
@role_required("ADMIN")
def search_companies():
    query = request.args.get("q", "").strip()
    page, per_page = _pagination_args()
    cache_key = f"admin_companies:{query}:{page}:{per_page}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    companies_query = CompanyProfile.query.join(User)
    if query:
        like = f"%{query}%"
        companies_query = companies_query.filter(
            or_(CompanyProfile.company_name.ilike(like), User.email.ilike(like), User.full_name.ilike(like))
        )

    companies_pagination = companies_query.order_by(CompanyProfile.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    payload = _paginated_response(
        companies_pagination,
        [
            {
                "id": c.id,
                "company_name": c.company_name,
                "hr_contact": c.hr_contact,
                "approval_status": c.approval_status,
                "user_id": c.user_id,
                "active": c.user.is_active,
                "blacklisted": c.user.is_blacklisted,
            }
            for c in companies_pagination.items
        ],
    )
    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass
    return jsonify(payload)


@admin_bp.get("/students")
@role_required("ADMIN")
def search_students():
    query = request.args.get("q", "").strip()
    page, per_page = _pagination_args()
    cache_key = f"admin_students:{query}:{page}:{per_page}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    students_query = StudentProfile.query.join(User)
    if query:
        like = f"%{query}%"
        students_query = students_query.filter(or_(User.full_name.ilike(like), User.email.ilike(like), StudentProfile.branch.ilike(like)))

    students_pagination = students_query.order_by(StudentProfile.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    payload = _paginated_response(
        students_pagination,
        [
            {
                "id": s.id,
                "user_id": s.user_id,
                "name": s.user.full_name,
                "email": s.user.email,
                "branch": s.branch,
                "cgpa": s.cgpa,
                "graduation_year": s.graduation_year,
                "active": s.user.is_active,
                "blacklisted": s.user.is_blacklisted,
            }
            for s in students_pagination.items
        ],
    )
    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass
    return jsonify(payload)


@admin_bp.put("/users/<int:user_id>/status")
@role_required("ADMIN")
def update_user_status(user_id):
    data = request.get_json() or {}
    user = User.query.get_or_404(user_id)
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "is_blacklisted" in data:
        user.is_blacklisted = bool(data["is_blacklisted"])
    db.session.commit()
    _safe_cache_clear()
    return jsonify({"message": "User status updated"})


@admin_bp.get("/applications")
@role_required("ADMIN")
def list_applications():
    page, per_page = _pagination_args()
    cache_key = f"admin_applications:{page}:{per_page}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    applications_pagination = Application.query.order_by(Application.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    payload = _paginated_response(
        applications_pagination,
        [
            {
                "id": a.id,
                "student": a.student.user.full_name,
                "student_email": a.student.user.email,
                "company": a.drive.company.company_name,
                "drive_title": a.drive.job_title,
                "status": a.status,
                "applied_at": a.application_date.isoformat(),
            }
            for a in applications_pagination.items
        ],
    )
    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass
    return jsonify(payload)


@admin_bp.get("/drives")
@role_required("ADMIN")
def list_drives():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip().upper()
    page, per_page = _pagination_args()
    cache_key = f"admin_drives:{query}:{status}:{page}:{per_page}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    drives_query = PlacementDrive.query.join(CompanyProfile)
    if query:
        like = f"%{query}%"
        drives_query = drives_query.filter(
            or_(
                PlacementDrive.job_title.ilike(like),
                PlacementDrive.eligible_branch.ilike(like),
                CompanyProfile.company_name.ilike(like),
            )
        )
    if status in {"PENDING", "APPROVED", "REJECTED", "CLOSED"}:
        drives_query = drives_query.filter(PlacementDrive.status == status)

    drives_pagination = drives_query.order_by(PlacementDrive.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    payload = _paginated_response(
        drives_pagination,
        [
            {
                "id": d.id,
                "company_id": d.company_id,
                "company": d.company.company_name,
                "job_title": d.job_title,
                "eligible_branch": d.eligible_branch,
                "min_cgpa": d.min_cgpa,
                "eligible_year": d.eligible_year,
                "deadline": d.application_deadline.isoformat(),
                "status": d.status,
            }
            for d in drives_pagination.items
        ],
    )
    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass
    return jsonify(payload)


@admin_bp.get("/stats")
@role_required("ADMIN")
def placement_stats():
    cache_key = "admin_placement_stats"
    try:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)
    except Exception:
        pass

    total_apps = Application.query.count()
    shortlisted = Application.query.filter_by(status="SHORTLISTED").count()
    selected = Application.query.filter_by(status="SELECTED").count()
    rejected = Application.query.filter_by(status="REJECTED").count()

    company_summary_rows = (
        db.session.query(CompanyProfile.company_name, func.count(Application.id).label("selected_count"))
        .join(PlacementDrive, PlacementDrive.company_id == CompanyProfile.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .filter(Application.status == "SELECTED")
        .group_by(CompanyProfile.company_name)
        .order_by(desc("selected_count"))
        .limit(10)
        .all()
    )

    payload = {
        "total_applications": total_apps,
        "shortlisted": shortlisted,
        "selected": selected,
        "rejected": rejected,
        "selection_rate": round((selected / total_apps) * 100, 2) if total_apps else 0,
        "top_companies_by_selections": [
            {"company": row.company_name, "selected_count": row.selected_count}
            for row in company_summary_rows
        ],
    }
    try:
        cache.set(cache_key, payload, timeout=120)
    except Exception:
        pass
    return jsonify(payload)


@admin_bp.post("/reports/export")
@role_required("ADMIN")
def export_report():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    start_raw = str(data.get("start_date", "")).strip()
    end_raw = str(data.get("end_date", "")).strip()

    start_dt, start_err = _parse_date_param(start_raw, "start_date")
    if start_err:
        return jsonify({"message": start_err}), 400

    end_dt, end_err = _parse_date_param(end_raw, "end_date")
    if end_err:
        return jsonify({"message": end_err}), 400

    if start_dt is None or end_dt is None:
        return jsonify({"message": "Invalid date range"}), 400

    if end_dt < start_dt:
        return jsonify({"message": "end_date must be on or after start_date"}), 400

    task_id = uuid4().hex
    log = AsyncTaskLog()
    log.user_id = user_id
    log.task_id = task_id
    log.task_type = "EXPORT_ADMIN_REPORT"
    log.status = "PENDING"
    db.session.add(log)
    db.session.commit()

    try:
        celery_app = current_app.extensions["celery"]
        celery_app.send_task("app.tasks.export_admin_activity_report_task", args=[user_id, start_raw, end_raw], task_id=task_id)
    except Exception:
        db.session.delete(log)
        db.session.commit()
        return jsonify({"message": "Report export queue is currently unavailable"}), 503

    return jsonify({"message": "Report export started", "task_id": task_id}), 202


@admin_bp.get("/reports/tasks/<task_id>")
@role_required("ADMIN")
def report_task_status(task_id):
    user_id = int(get_jwt_identity())
    log = AsyncTaskLog.query.filter_by(user_id=user_id, task_id=task_id, task_type="EXPORT_ADMIN_REPORT").first_or_404()
    return jsonify({"task_id": log.task_id, "status": log.status, "result_path": log.result_path})


@admin_bp.get("/reports/tasks/<task_id>/download")
@role_required("ADMIN")
def download_report(task_id):
    user_id = int(get_jwt_identity())
    log = AsyncTaskLog.query.filter_by(user_id=user_id, task_id=task_id, task_type="EXPORT_ADMIN_REPORT").first_or_404()
    if log.status != "COMPLETED" or not log.result_path:
        return jsonify({"message": "Report is not ready yet"}), 400

    file_path = Path(log.result_path)
    if not file_path.is_absolute():
        file_path = Path(current_app.root_path).parent / file_path
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"message": "Report file not found"}), 404

    return send_file(file_path, as_attachment=True, download_name=file_path.name, mimetype="text/csv")
