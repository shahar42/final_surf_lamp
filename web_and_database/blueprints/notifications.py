import json
import os
import logging
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, session
from pywebpush import webpush, WebPushException
from data_base import SessionLocal, User, NotificationSubscription
from utils.decorators import admin_required

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# Use Env Var for Private Key (Security Best Practice)
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
# Fallback for local dev if file exists
VAPID_PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vapid_private_key.pem')

# Public Key
VAPID_PUBLIC_KEY = 'BEbp72z3GNmxbrIyhvpCxnmUcA-g5NQG_eYLy_TuF8E-JnLI0u6K54hgLB0E7Uui8xSPV4xqYj1gz95bmk7E48g'
VAPID_CLAIMS = {
    "sub": "mailto:admin@surflamp.com"
}

def get_private_key_content():
    """Retrieve VAPID private key content from Env Var or File and normalize it"""
    key = VAPID_PRIVATE_KEY
    if not key and os.path.exists(VAPID_PRIVATE_KEY_PATH):
        try:
            with open(VAPID_PRIVATE_KEY_PATH, 'r') as f:
                key = f.read().strip()
        except Exception:
            pass
            
    if key:
        # Normalize: Handle escaped newlines (\n) and physical newlines
        key = key.replace("\\n", "\n")
        
        # Strip all headers, footers, and whitespace to get raw base64
        raw_b64 = key.replace("-----BEGIN PRIVATE KEY-----", "")\
                     .replace("-----END PRIVATE KEY-----", "")\
                     .replace("\n", "")\
                     .replace("\r", "")\
                     .replace(" ", "")\
                     .strip()
        
        # Re-wrap to standard PEM format (64 chars per line)
        wrapped = "\n".join([raw_b64[i:i+64] for i in range(0, len(raw_b64), 64)])
        return f"-----BEGIN PRIVATE KEY-----\n{wrapped}\n-----END PRIVATE KEY-----"
            
    return key

def trigger_push_broadcast(message, target_location=None):
    """
    Send a push notification to all users or those in a specific location.
    Called by admin.py.
    Uses Database (Scott Meyers approved).
    """
    private_key_content = get_private_key_content()
    if not private_key_content:
        logging.error("Cannot send push: Missing Private Key")
        return 0

    # Write key to a temporary file to ensure pywebpush handles it correctly
    # (Avoids string/bytes/DER confusion)
    temp_pem_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.pem') as temp_pem:
            temp_pem.write(private_key_content)
            # Ensure a trailing newline just in case
            if not private_key_content.endswith('\n'):
                temp_pem.write('\n')
            temp_pem_path = temp_pem.name
    except Exception as e:
        logging.error(f"Failed to create temp key file: {e}")
        return 0

    db = SessionLocal()
    sent_count = 0
    
    try:
        # Build Query
        query = db.query(NotificationSubscription, User).join(User)
        
        # Apply Location Filter if needed
        if target_location and target_location != 'all':
            # Loose matching: if user location contains the target string
            # e.g., "Tel Aviv" matches "Tel Aviv, Israel"
            query = query.filter(User.location.ilike(f"%{target_location}%"))
            
        subscriptions = query.all()
        
        for sub_record, user in subscriptions:
            # Reconstruct subscription info object required by pywebpush
            sub_info = {
                "endpoint": sub_record.endpoint,
                "keys": {
                    "p256dh": sub_record.p256dh,
                    "auth": sub_record.auth
                }
            }
            
            try:
                webpush(
                    subscription_info=sub_info,
                    data=json.dumps({
                        'title': 'Surf Lamp Alert', 
                        'body': message,
                        'url': '/' 
                    }),
                    vapid_private_key=temp_pem_path, # Pass the FILE PATH
                    vapid_claims=VAPID_CLAIMS
                )
                sent_count += 1
            except WebPushException as ex:
                if ex.response and ex.response.status_code in [403, 404, 410]:
                    # Subscription expired/gone/invalid - delete from DB
                    # 403: Forbidden (Key mismatch)
                    # 404: Not Found
                    # 410: Gone (Unsubscribed)
                    logging.info(f"Deleting invalid subscription (Status {ex.response.status_code}) for user {sub_record.user_id}")
                    db.delete(sub_record)
                else:
                    logging.warning(f"Push failed for user {sub_record.user_id}: {ex}")
            except Exception as e:
                logging.error(f"Push error: {e}")

        db.commit() # Commit any deletions
        
    except Exception as e:
        logging.error(f"Broadcasting error: {e}")
        db.rollback()
    finally:
        db.close()
        # Clean up temp file
        if temp_pem_path and os.path.exists(temp_pem_path):
            try:
                os.unlink(temp_pem_path)
            except Exception:
                pass

    logging.info(f"Push Broadcast Sent: {sent_count} messages (Target: {target_location})")
    return sent_count

@bp.route('/vapid-public-key')
def get_vapid_key():
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})

@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Save subscription to the Database.
    Requires user to be logged in (session['user_id']).
    """
    subscription_info = request.json
    if not subscription_info:
        return jsonify({'error': 'No subscription info provided'}), 400
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User must be logged in to subscribe'}), 401
        
    endpoint = subscription_info.get('endpoint')
    keys = subscription_info.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')
    
    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Invalid subscription data'}), 400

    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(NotificationSubscription).filter_by(endpoint=endpoint).first()
        if existing:
            # Update keys if changed (rare but possible)
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_id = user_id # Update owner if changed
        else:
            new_sub = NotificationSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth
            )
            db.add(new_sub)
        
        db.commit()
        logging.info(f"Subscription saved for user {user_id}")
        return jsonify({'status': 'success'}), 201
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to save subscription: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        db.close()

@bp.route('/send-test', methods=['POST'])
@admin_required
def send_test_notification():
    # Admin debug endpoint. Pushes to EVERY subscriber, so it must never be
    # reachable anonymously or by a regular user.
    message = request.json.get('message', 'Test notification')
    count = trigger_push_broadcast(message, target_location='all')
    return jsonify({'status': 'success', 'sent_count': count})
