import logging
import time
import google.generativeai as genai
from flask import Blueprint, request, jsonify, session, current_app
from data_base import SessionLocal, User, Arduino, Location
from utils.decorators import login_required
from chat_logic import build_chat_context

logger = logging.getLogger(__name__)

bp = Blueprint('api_chat', __name__)

@bp.route("/api/chat", methods=['POST'])
@login_required
def chat():
    if not current_app.config.get('CHAT_BOT_ENABLED'):
        return jsonify({"error": "Chat disabled"}), 503

    if not current_app.config.get('GEMINI_API_KEY'):
        return jsonify({"error": "Chat not configured"}), 503

    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"error": "Message required"}), 400

        user_email = session.get('user_email')
        if not user_email:
            return jsonify({"error": "Not authenticated"}), 401

        cache_key = f'chat_user_data_{user_email}'
        cached_data = session.get(cache_key)
        cache_time = session.get(f'{cache_key}_time', 0)

        if cached_data and (time.time() - cache_time) < 300:
            user_data = cached_data['user']
            conditions_data = cached_data['conditions']
        else:
            db = SessionLocal()
            try:
                user_data = db.query(User).filter(User.email == user_email).first()
                if not user_data:
                    return jsonify({"error": "User not found"}), 404

                conditions_data = db.query(Location).filter(
                    Location.location == user_data.location
                ).first()

                session[cache_key] = {
                    'user': user_data,
                    'conditions': conditions_data
                }
                session[f'{cache_key}_time'] = time.time()

            finally:
                db.close()

        system_prompt = build_chat_context(user_data, conditions_data, user_message)

        model_name = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
        model = genai.GenerativeModel(model_name)
        chat_session = model.start_chat(history=[])

        full_prompt = f"{system_prompt}\n\nUser question: {user_message}"
        response = chat_session.send_message(full_prompt)

        return jsonify({
            "response": response.text,
            "success": True
        }), 200

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": "Failed to process chat request"}), 500

@bp.route("/api/chat/status", methods=['GET'])
def chat_status():
    enabled = current_app.config.get('CHAT_BOT_ENABLED') and current_app.config.get('GEMINI_API_KEY') is not None
    return jsonify({"enabled": enabled}), 200