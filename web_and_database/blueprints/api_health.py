"""Health check endpoint for monitoring."""
import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify
from data_base import SessionLocal, Arduino, RedisHealth
from sqlalchemy import text
from redis_manager import get_redis_client

logger = logging.getLogger(__name__)
bp = Blueprint('api_health', __name__)

@bp.route("/api/health", methods=['GET'])
def health_check():
    """Comprehensive health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "metrics": {}
    }

    # Check Database
    db_start = datetime.now(timezone.utc)
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_latency = (datetime.now(timezone.utc) - db_start).total_seconds() * 1000
        health_status["services"]["database"] = {
            "status": "healthy" if db_latency < 1000 else "degraded",
            "latency_ms": int(db_latency)
        }
        db.close()
    except Exception as e:
        health_status["services"]["database"] = {"status": "down", "error": str(e)}
        health_status["status"] = "unhealthy"

    # Check Redis
    redis_start = datetime.now(timezone.utc)
    try:
        redis = get_redis_client()
        if redis:
            redis.ping()
            redis_latency = (datetime.now(timezone.utc) - redis_start).total_seconds() * 1000
            health_status["services"]["redis"] = {
                "status": "healthy" if redis_latency < 100 else "degraded",
                "latency_ms": int(redis_latency)
            }
        else:
            health_status["services"]["redis"] = {"status": "down", "error": "Redis client unavailable"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["redis"] = {"status": "down", "error": str(e)}
        health_status["status"] = "degraded"

    # Check Processor Heartbeat
    try:
        db = SessionLocal()
        result = db.execute(text(
            "SELECT last_alive_timestamp FROM processor_heartbeat WHERE service_name = 'surf-lamp-processor'"
        )).fetchone()
        if result:
            last_heartbeat = result[0]
            age_seconds = (datetime.now(timezone.utc) - last_heartbeat.replace(tzinfo=timezone.utc)).total_seconds()
            health_status["services"]["processor"] = {
                "status": "healthy" if age_seconds < 180 else "stale",
                "last_heartbeat": last_heartbeat.isoformat(),
                "age_seconds": int(age_seconds)
            }
        else:
            health_status["services"]["processor"] = {"status": "unknown", "error": "No heartbeat found"}
        db.close()
    except Exception as e:
        health_status["services"]["processor"] = {"status": "error", "error": str(e)}

    # Metrics
    try:
        db = SessionLocal()
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Count active Arduinos (polled in last hour)
        active_count = db.query(Arduino).filter(Arduino.last_poll_time >= one_hour_ago).count()
        total_count = db.query(Arduino).count()

        health_status["metrics"] = {
            "active_arduinos": active_count,
            "total_arduinos": total_count,
            "stale_arduinos": total_count - active_count
        }
        db.close()
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")

    # Overall status
    if any(svc.get("status") == "down" for svc in health_status["services"].values()):
        health_status["status"] = "unhealthy"
    elif any(svc.get("status") in ["degraded", "stale"] for svc in health_status["services"].values()):
        health_status["status"] = "degraded"

    status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
    return jsonify(health_status), status_code
