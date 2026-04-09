from datetime import datetime, timedelta
from pathlib import Path

from celery import current_task, shared_task
from flask import current_app

from .extensions import db
from .models import Application, AsyncTaskLog, PlacementDrive, StudentProfile, User
from .utils import send_email, send_google_chat_message, write_csv


@shared_task(name="app.tasks.send_daily_student_reminders")
def send_daily_student_reminders():
    now = datetime.utcnow()
    upcoming = now + timedelta(days=2)
    drives = (
        PlacementDrive.query.filter(PlacementDrive.status == "APPROVED")
        .filter(PlacementDrive.application_deadline >= now)
        .filter(PlacementDrive.application_deadline <= upcoming)
        .all()
    )

    if not drives:
        return {"sent": 0}

    students = StudentProfile.query.join(User).filter(User.is_active.is_(True), User.is_blacklisted.is_(False)).all()
    sent = 0
    for student in students:
        eligible_drives = [
            d
            for d in drives
            if d.eligible_branch == student.branch and d.eligible_year == student.graduation_year and student.cgpa >= d.min_cgpa
        ]
        if not eligible_drives:
            continue

        body = "<h3>Upcoming placement deadlines</h3><ul>"
        lines = ["Upcoming placement deadlines:"]
        for drive in eligible_drives:
            body += f"<li>{drive.company.company_name} - {drive.job_title} (Deadline: {drive.application_deadline.date()})</li>"
            lines.append(f"- {drive.company.company_name} | {drive.job_title} | Deadline: {drive.application_deadline.date()}")
        body += "</ul>"
        send_email(current_app.config, student.user.email, "Placement deadline reminders", body)
        send_google_chat_message(
            current_app.config,
            f"Student reminder sent to {student.user.email}\n" + "\n".join(lines),
        )
        sent += 1

    return {"sent": sent}


@shared_task(name="app.tasks.send_monthly_admin_report")
def send_monthly_admin_report():
    month_start = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)
    drives_count = PlacementDrive.query.filter(PlacementDrive.created_at >= month_start).count()
    applied_count = Application.query.filter(Application.application_date >= month_start).count()
    selected_count = (
        Application.query.filter(Application.application_date >= month_start)
        .filter(Application.status == "SELECTED")
        .count()
    )

    body = f"""
    <h2>Monthly Placement Activity Report</h2>
    <p>Drives created: {drives_count}</p>
    <p>Total applications: {applied_count}</p>
    <p>Total selected: {selected_count}</p>
    """
    send_email(current_app.config, current_app.config["ADMIN_EMAIL"], "Monthly Placement Report", body)
    return {"drives": drives_count, "applications": applied_count, "selected": selected_count}


@shared_task(name="app.tasks.export_student_applications_task")
def export_student_applications_task(user_id: int):
    task_id = getattr(getattr(current_task, "request", None), "id", None)
    task_log = AsyncTaskLog.query.filter_by(task_id=task_id).first()
    if task_log:
        task_log.status = "IN_PROGRESS"
        db.session.commit()

    try:
        student = StudentProfile.query.filter_by(user_id=user_id).first()
        if not student:
            if task_log:
                task_log.status = "FAILED"
                db.session.commit()
            return {"error": "Student not found"}

        applications = Application.query.filter_by(student_id=student.id).all()
        rows = []
        for app_row in applications:
            latest_status_change = (
                app_row.status_history[-1].changed_at.isoformat()
                if app_row.status_history
                else app_row.application_date.isoformat()
            )
            rows.append(
                {
                    "student_id": student.id,
                    "company_name": app_row.drive.company.company_name,
                    "drive_title": app_row.drive.job_title,
                    "application_status": app_row.status,
                    "applied_date": app_row.application_date.isoformat(),
                    "latest_status_change_date": latest_status_change,
                }
            )

        file_name = f"student_{student.id}_applications_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
        export_dir = Path("exports")
        file_path = export_dir / file_name
        write_csv(
            str(file_path),
            rows,
            [
                "student_id",
                "company_name",
                "drive_title",
                "application_status",
                "applied_date",
                "latest_status_change_date",
            ],
        )

        if task_log:
            task_log.status = "COMPLETED"
            task_log.result_path = str(file_path)
            db.session.commit()

        send_email(
            current_app.config,
            student.user.email,
            "Your placement applications export is ready",
            f"<p>Your export file is ready: {file_name}</p>",
        )
        return {"file_path": str(file_path)}
    except Exception:
        db.session.rollback()
        if task_log:
            task_log.status = "FAILED"
            db.session.commit()
        raise


@shared_task(name="app.tasks.export_admin_activity_report_task")
def export_admin_activity_report_task(user_id: int, start_date: str, end_date: str):
    task_id = getattr(getattr(current_task, "request", None), "id", None)
    task_log = AsyncTaskLog.query.filter_by(task_id=task_id).first()
    if task_log:
        task_log.status = "IN_PROGRESS"
        db.session.commit()

    try:
        admin_user = User.query.filter_by(id=user_id, role="ADMIN").first()
        if not admin_user:
            if task_log:
                task_log.status = "FAILED"
                db.session.commit()
            return {"error": "Admin user not found"}

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            if task_log:
                task_log.status = "FAILED"
                db.session.commit()
            return {"error": "Invalid date format"}

        if end_dt < start_dt:
            if task_log:
                task_log.status = "FAILED"
                db.session.commit()
            return {"error": "end_date must be on or after start_date"}

        end_exclusive = end_dt + timedelta(days=1)

        drives = (
            PlacementDrive.query.filter(PlacementDrive.created_at >= start_dt)
            .filter(PlacementDrive.created_at < end_exclusive)
            .order_by(PlacementDrive.created_at.asc())
            .all()
        )
        applications = (
            Application.query.filter(Application.application_date >= start_dt)
            .filter(Application.application_date < end_exclusive)
            .order_by(Application.application_date.asc())
            .all()
        )

        selected_count = sum(1 for app_row in applications if app_row.status == "SELECTED")

        rows = [
            {
                "row_type": "SUMMARY",
                "report_start_date": start_date,
                "report_end_date": end_date,
                "total_drives": len(drives),
                "total_applications": len(applications),
                "total_selected": selected_count,
                "company_name": "",
                "drive_title": "",
                "student_email": "",
                "application_status": "",
                "event_date": "",
            }
        ]

        for drive in drives:
            rows.append(
                {
                    "row_type": "DRIVE",
                    "report_start_date": start_date,
                    "report_end_date": end_date,
                    "total_drives": "",
                    "total_applications": "",
                    "total_selected": "",
                    "company_name": drive.company.company_name,
                    "drive_title": drive.job_title,
                    "student_email": "",
                    "application_status": drive.status,
                    "event_date": drive.created_at.isoformat(),
                }
            )

        for app_row in applications:
            rows.append(
                {
                    "row_type": "APPLICATION",
                    "report_start_date": start_date,
                    "report_end_date": end_date,
                    "total_drives": "",
                    "total_applications": "",
                    "total_selected": "",
                    "company_name": app_row.drive.company.company_name,
                    "drive_title": app_row.drive.job_title,
                    "student_email": app_row.student.user.email,
                    "application_status": app_row.status,
                    "event_date": app_row.application_date.isoformat(),
                }
            )

        file_name = f"admin_report_{start_date}_to_{end_date}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
        export_dir = Path("exports")
        file_path = export_dir / file_name
        write_csv(
            str(file_path),
            rows,
            [
                "row_type",
                "report_start_date",
                "report_end_date",
                "total_drives",
                "total_applications",
                "total_selected",
                "company_name",
                "drive_title",
                "student_email",
                "application_status",
                "event_date",
            ],
        )

        if task_log:
            task_log.status = "COMPLETED"
            task_log.result_path = str(file_path)
            db.session.commit()

        send_email(
            current_app.config,
            admin_user.email,
            "Admin activity report is ready",
            f"<p>Your report for {start_date} to {end_date} is ready: {file_name}</p>",
        )
        return {"file_path": str(file_path)}
    except Exception:
        db.session.rollback()
        if task_log:
            task_log.status = "FAILED"
            db.session.commit()
        raise
