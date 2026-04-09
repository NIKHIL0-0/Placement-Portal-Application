from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from .models import User


def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or not user.is_active or user.is_blacklisted:
                return jsonify({"message": "User inactive or blocked"}), 403
            if user.role not in roles:
                return jsonify({"message": "Forbidden"}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper
