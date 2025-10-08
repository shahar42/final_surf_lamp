"""
Manufacturing Dashboard for Surf Lamp Production

Web interface for managing Arduino IDs and generating QR codes.
"""

from flask import Flask, render_template, request, jsonify, send_file
from id_manager import IDManager
from qr_generator import QRGenerator
import logging
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'manufacturing-key-change-in-production')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
id_manager = IDManager()
qr_generator = QRGenerator()


@app.route('/')
def index():
    """Manufacturing dashboard home page"""
    try:
        stats = id_manager.get_id_statistics()
        recent_ids = id_manager.get_used_ids(limit=10)

        return render_template('dashboard.html',
                             stats=stats,
                             recent_ids=recent_ids)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html',
                             stats={"error": str(e)},
                             recent_ids=[])


@app.route('/api/next-id')
def get_next_id():
    """API endpoint to get next available Arduino ID"""
    try:
        next_id = id_manager.get_next_available_id()
        return jsonify({"success": True, "next_id": next_id})
    except Exception as e:
        logger.error(f"Error getting next ID: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/check-id/<int:arduino_id>')
def check_id(arduino_id):
    """Check if a specific Arduino ID is available"""
    try:
        is_available = id_manager.is_id_available(arduino_id)
        return jsonify({"success": True, "arduino_id": arduino_id, "available": is_available})
    except Exception as e:
        logger.error(f"Error checking ID {arduino_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    """Generate QR code for a specific Arduino ID with duplicate checking"""
    try:
        data = request.get_json()
        arduino_id = data.get('arduino_id')

        if not arduino_id:
            return jsonify({"success": False, "error": "arduino_id required"}), 400

        arduino_id = int(arduino_id)

        # Check if ID already exists in database
        is_available = id_manager.is_id_available(arduino_id)

        if not is_available:
            # ID already registered - show warning
            next_id = id_manager.get_next_available_id()
            return jsonify({
                "success": False,
                "error": f"Arduino ID {arduino_id} is already registered in the database",
                "warning": True,
                "next_available_id": next_id,
                "suggestion": f"Use ID {next_id} instead"
            }), 409  # 409 Conflict

        # ID is available - generate QR code
        filepath = qr_generator.generate_qr_code(arduino_id)

        # Return relative path for web display
        filename = os.path.basename(filepath)
        web_path = f"/static/qr_codes/{filename}"

        return jsonify({
            "success": True,
            "arduino_id": arduino_id,
            "qr_code_path": web_path,
            "download_url": f"/download-qr/{arduino_id}"
        })

    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/generate-batch', methods=['POST'])
def generate_batch():
    """Generate batch of QR codes (auto-skips duplicates)"""
    try:
        data = request.get_json()
        start_id = int(data.get('start_id', 1))
        end_id = int(data.get('end_id', 10))

        if end_id < start_id:
            return jsonify({"success": False, "error": "end_id must be >= start_id"}), 400

        if (end_id - start_id) > 100:
            return jsonify({"success": False, "error": "Maximum batch size is 100"}), 400

        # Check which IDs are available (skip duplicates)
        ids_to_generate = []
        skipped_ids = []

        for arduino_id in range(start_id, end_id + 1):
            if id_manager.is_id_available(arduino_id):
                ids_to_generate.append(arduino_id)
            else:
                skipped_ids.append(arduino_id)

        # Generate QR codes only for available IDs
        paths = []
        for arduino_id in ids_to_generate:
            path = qr_generator.generate_qr_code(arduino_id)
            paths.append(path)

        response = {
            "success": True,
            "count": len(paths),
            "start_id": start_id,
            "end_id": end_id,
            "generated": len(paths),
            "skipped": len(skipped_ids)
        }

        if skipped_ids:
            response["skipped_ids"] = skipped_ids
            response["message"] = f"Generated {len(paths)} QR codes. Skipped {len(skipped_ids)} already registered IDs."

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error generating batch: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/generate-print-sheet', methods=['POST'])
def generate_print_sheet():
    """Generate print-ready sheet with multiple QR codes"""
    try:
        data = request.get_json()
        start_id = int(data.get('start_id', 1))
        end_id = int(data.get('end_id', 9))
        cols = int(data.get('cols', 3))

        arduino_ids = list(range(start_id, end_id + 1))
        filepath = qr_generator.generate_print_sheet(arduino_ids, cols=cols)

        filename = os.path.basename(filepath)
        web_path = f"/static/qr_codes/{filename}"

        return jsonify({
            "success": True,
            "print_sheet_path": web_path,
            "count": len(arduino_ids)
        })

    except Exception as e:
        logger.error(f"Error generating print sheet: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/download-qr/<int:arduino_id>')
def download_qr(arduino_id):
    """Download QR code image"""
    try:
        filename = f"arduino_{arduino_id}.png"
        filepath = os.path.join(qr_generator.output_dir, filename)

        if not os.path.exists(filepath):
            # Generate if doesn't exist
            filepath = qr_generator.generate_qr_code(arduino_id)

        return send_file(filepath, as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f"Error downloading QR code: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get manufacturing statistics"""
    try:
        stats = id_manager.get_id_statistics()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5001, debug=True)
