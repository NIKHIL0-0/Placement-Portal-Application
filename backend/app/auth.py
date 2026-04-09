import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from .extensions import db
from .models import CompanyProfile, StudentProfile, User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_common_fields(data):
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not EMAIL_RE.match(email):
        return "Invalid email format"
    if len(password) < 6:
        return "Password must be at least 6 characters"
    return ""


def _validate_student_fields(data):
    try:
        cgpa = float(data.get("cgpa"))
    except (TypeError, ValueError):
        return "CGPA must be a number"
    if cgpa < 0 or cgpa > 10:
        return "CGPA must be between 0 and 10"

    try:
        year = int(data.get("graduation_year"))
    except (TypeError, ValueError):
        return "Graduation year must be a valid year"
    if year < 2020 or year > 2100:
        return "Graduation year must be between 2020 and 2100"
    return ""


def _validate_company_fields(data):
    website = data.get("website")
    if website and not str(website).startswith(("http://", "https://")):
        return "Website must start with http:// or https://"
    return ""


def _validate_registration_payload(payload, role):
    required = ["full_name", "email", "password"]
    if role == "STUDENT":
        required.extend(["branch", "cgpa", "graduation_year"])
    if role == "COMPANY":
        required.extend(["company_name", "hr_contact"])

    missing = [field for field in required if field not in payload or payload[field] in (None, "")]
    return missing


@auth_bp.post("/register/student")
def register_student():
    data = request.get_json() or {}
    missing = _validate_registration_payload(data, "STUDENT")
    if missing:
        return jsonify({"message": "Missing fields", "fields": missing}), 400

    common_error = _validate_common_fields(data)
    if common_error:
        return jsonify({"message": common_error}), 400

    student_error = _validate_student_fields(data)
    if student_error:
        return jsonify({"message": student_error}), 400

    if User.query.filter_by(email=data["email"].strip().lower()).first():
        return jsonify({"message": "Email already exists"}), 409

    user = User(
        email=data["email"].strip().lower(),
        role="STUDENT",
        full_name=data["full_name"].strip(),
    )
    user.set_password(data["password"])

    profile = StudentProfile(
        user=user,
        branch=data["branch"].strip(),
        cgpa=float(data["cgpa"]),
        graduation_year=int(data["graduation_year"]),
        resume_url=data.get("resume_url"),
    )

    db.session.add(user)
    db.session.add(profile)
    db.session.commit()
    return jsonify({"message": "Student registered successfully"}), 201


@auth_bp.post("/register/company")
def register_company():
    data = request.get_json() or {}
    missing = _validate_registration_payload(data, "COMPANY")
    if missing:
        return jsonify({"message": "Missing fields", "fields": missing}), 400

    common_error = _validate_common_fields(data)
    if common_error:
        return jsonify({"message": common_error}), 400

    company_error = _validate_company_fields(data)
    if company_error:
        return jsonify({"message": company_error}), 400

    if User.query.filter_by(email=data["email"].strip().lower()).first():
        return jsonify({"message": "Email already exists"}), 409

    user = User(
        email=data["email"].strip().lower(),
        role="COMPANY",
        full_name=data["full_name"].strip(),
    )
    user.set_password(data["password"])

    profile = CompanyProfile(
        user=user,
        company_name=data["company_name"].strip(),
        hr_contact=data["hr_contact"].strip(),
        website=data.get("website"),
        approval_status="PENDING",
    )

    db.session.add(user)
    db.session.add(profile)
    db.session.commit()
    return jsonify({"message": "Company registered successfully. Waiting for admin approval."}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.is_active or user.is_blacklisted:
        return jsonify({"message": "User inactive or blocked"}), 403

    if user.role == "COMPANY":
        company = user.company_profile
        if not company or company.approval_status != "APPROVED":
            return jsonify({"message": "Company not approved by admin"}), 403

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"access_token": token, "user": {"id": user.id, "role": user.role, "name": user.full_name}})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify({"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name})
