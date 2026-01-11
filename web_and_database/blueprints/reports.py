import logging
from flask import Blueprint, request, session
from config import limiter
from utils.decorators import login_required
from data_base import SessionLocal, ErrorReport, get_user_lamp_data

logger = logging.getLogger(__name__)

bp = Blueprint('reports', __name__)

@bp.route("/report-error", methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def report_error():
    """User-submitted error reporting with auto-captured context"""
    try:
        data = request.get_json()
        error_description = data.get('error_description', '').strip()

        # Validate input
        if not error_description:
            return {'success': False, 'message': 'Error description is required'}, 400

        if len(error_description) > 1000:
            return {'success': False, 'message': 'Error description too long (max 1000 characters)'}, 400

        user_email = session.get('user_email')

        # Get additional context
        db = SessionLocal()
        try:
            user, arduinos, _ = get_user_lamp_data(user_email)

            if not user:
                return {'success': False, 'message': 'User not found'}, 404

            # Get first arduino if user has any (most users have just one)
            arduino_id = arduinos[0].arduino_id if arduinos else None

            error_report = ErrorReport(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                arduino_id=arduino_id,
                location=user.location,
                user_agent=request.headers.get('User-Agent', 'Unknown'),
                error_description=error_description
            )

            db.add(error_report)
            db.commit()

            logger.info(f"Error report saved from user {user.username} (ID: {user.user_id})")
            return {'success': True, 'message': 'Error report submitted successfully. Thank you!'}, 200

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in report_error endpoint: {e}")
        return {'success': False, 'message': f'Server error: {str(e)}'}, 500
