import json
import os
import logging
from flask import Blueprint, request, jsonify, current_app
from pywebpush import webpush, WebPushException

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

SUBSCRIPTIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'subscriptions.json')
# Use Env Var for Private Key (Security Best Practice)
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
# Fallback for local dev if file exists
VAPID_PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vapid_private_key.pem')

# NEW Public Key
VAPID_PUBLIC_KEY = 'BIg41PcUdRtbt6wOO8CpOJKmbgH4PA_ULHRC_dWI2z65tDY1h_We6rOkbzW0Ime6eFxKVQGhn0XVAa0oOKLq7Y4'
VAPID_CLAIMS = {
    "sub": "mailto:admin@surflamp.com"
}

def get_subscriptions():
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return []
    try:
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading subscriptions: {e}")
        return []

def save_subscription(sub_info):
    subs = get_subscriptions()
    # Check if already exists
    if sub_info not in subs:
        subs.append(sub_info)
        with open(SUBSCRIPTIONS_FILE, 'w') as f:
            json.dump(subs, f)
        return True
    return False

@bp.route('/vapid-public-key')
def get_vapid_key():
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})

@bp.route('/subscribe', methods=['POST'])
def subscribe():
    subscription_info = request.json
    if not subscription_info:
        return jsonify({'error': 'No subscription info provided'}), 400
    
    save_subscription(subscription_info)
    logging.info(f"New subscription received")
    return jsonify({'status': 'success'}), 201

@bp.route('/send-test', methods=['POST'])
def send_test_notification():
    # In production, secure this endpoint!
    message = request.json.get('message', 'Test notification from Surf Lamp!')
    subs = get_subscriptions()
    
    results = []
    
    # Determine Private Key source
    private_key = VAPID_PRIVATE_KEY
    if not private_key and os.path.exists(VAPID_PRIVATE_KEY_PATH):
        try:
            with open(VAPID_PRIVATE_KEY_PATH, 'r') as f:
                private_key = f.read().strip()
        except Exception as e:
            return jsonify({'error': f'Could not read private key file: {str(e)}'}), 500
            
    if not private_key:
        return jsonify({'error': 'VAPID Private Key is missing (Check Env Vars)'}), 500

    for sub_info in subs:
        try:
            webpush(
                subscription_info=sub_info,
                data=json.dumps({'title': 'Surf Lamp', 'body': message}),
                vapid_private_key=private_key,
                vapid_claims=VAPID_CLAIMS
            )
            results.append({'status': 'success'})
        except WebPushException as ex:
            logging.error(f"WebPush failed: {ex}")
            results.append({'status': 'failed', 'error': str(ex)})
        except Exception as e:
            logging.error(f"Error sending: {e}")
            results.append({'status': 'error', 'error': str(e)})
            
    return jsonify({'results': results})