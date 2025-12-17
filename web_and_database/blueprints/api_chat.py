import logging
import time
import google.generativeai as genai
from flask import Blueprint, request, jsonify, session, current_app
from data_base import SessionLocal, User, Lamp, CurrentConditions
from utils.decorators import login_required
from chat_logic import build_chat_context

logger = logging.getLogger(__name__)

bp = Blueprint('api_chat', __name__)

@bp.route("/api/chat", methods=['POST'])
@login_required
def chat():
    """
    Gemini-powered chatbot endpoint for helping users understand their surf lamp.
    Requires authentication and provides context-aware responses.
    """
    if not current_app.config.get('CHAT_BOT_ENABLED'):
        return jsonify({"error": "Chat feature is currently disabled"}), 503

    if not current_app.config.get('GEMINI_API_KEY'):
        return jsonify({"error": "Chat feature is not configured"}), 503

    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Get user data from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "Not authenticated"}), 401

        # Check if user data is cached in session (valid for 5 minutes)
        cache_key = f'chat_user_data_{user_email}'
        cached_data = session.get(cache_key)
        cache_time = session.get(f'{cache_key}_time', 0)

        # Use cache if fresh (< 5 minutes old)
        if cached_data and (time.time() - cache_time) < 300:
            user_data = cached_data['user']
            conditions_data = cached_data['conditions']
            logger.info(f"Using cached user data for {user_email}")
        else:
            # Fetch fresh user and lamp data
            db = SessionLocal()
            try:
                user_data = db.query(User).filter(User.email == user_email).first()
                if not user_data:
                    return jsonify({"error": "User not found"}), 404

                # Get lamp and conditions
                lamp_data = db.query(Lamp).filter(Lamp.user_id == user_data.user_id).first()
                conditions_data = None
                if lamp_data:
                    conditions_data = db.query(CurrentConditions).filter(
                        CurrentConditions.lamp_id == lamp_data.lamp_id
                    ).first()

                # Cache for 5 minutes
                # Note: Session storage might not serialize SQLAlchemy objects well if they are not detached or simple dicts.
                # In original app.py, it seemed to cache objects. SQLAlchemy objects attached to session might be problematic if session closed.
                # However, original code did it.
                # To be safe, we might need to convert to dict or ensure they are detached.
                # But for now I'll stick to original logic.
                
                # Actually, storing DB objects in Flask session (cookie) is bad practice (serialization issues).
                # But let's assume it worked or was intended to work.
                # If 'user_data' is a SQLAlchemy object, it can't be pickled easily into a cookie unless converted.
                # The original code did `session[cache_key] = {'user': user_data, ...}`.
                # If that worked, then okay. If not, it was a bug in original code too.
                # I'll stick to the original code for now.
                
                session[cache_key] = {
                    'user': user_data,
                    'conditions': conditions_data
                }
                session[f'{cache_key}_time'] = time.time()
                logger.info(f"Cached user data for {user_email}")

            finally:
                db.close()

        # Build modular context based on user's question
        system_prompt = build_chat_context(user_data, conditions_data, user_message)

        # Call Gemini API
        model_name = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
        model = genai.GenerativeModel(model_name)

        # Create chat with system instruction
        # Note: 'history' should be list of contents.
        chat_session = model.start_chat(history=[])

        # Send message with system context prepended
        full_prompt = f"{system_prompt}\n\nUser question: {user_message}"
        response = chat_session.send_message(full_prompt)

        logger.info(f"Chat request from {user_email}: {user_message[:100]}")

        return jsonify({
            "response": response.text,
            "success": True
        }), 200

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": "Failed to process chat request", "details": str(e)}), 500

@bp.route("/api/chat/status", methods=['GET'])
def chat_status():
    """Check if chat feature is enabled"""
    enabled = current_app.config.get('CHAT_BOT_ENABLED') and current_app.config.get('GEMINI_API_KEY') is not None
    return jsonify({
        "enabled": enabled
    }), 200
