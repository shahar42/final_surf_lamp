"""
Beach search API endpoint for autocomplete functionality.

Author: shahar nitzan
"""

import logging
from flask import Blueprint, request, jsonify
from locations import search_beaches, get_all_beaches

logger = logging.getLogger(__name__)

bp = Blueprint('api_beaches', __name__)


@bp.route("/api/beaches/search", methods=['GET'])
def search_beaches_endpoint():
    """
    Search beaches for autocomplete.
    
    Query params:
        q: Search query (min 1 char)
        limit: Max results (default 10, max 27)
    
    Returns:
        List of matching beaches with name and coordinates
    """
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 27)
    
    if not query:
        # Return popular beaches when no query
        beaches = get_all_beaches()[:limit]
    else:
        beaches = search_beaches(query, limit=limit)
    
    # Format response
    results = [
        {
            'name': beach['english_name'],
            'hebrew_name': beach['hebrew_name'],
            'lat': beach['latitude'],
            'lng': beach['longitude']
        }
        for beach in beaches
    ]
    
    return jsonify({
        'success': True,
        'query': query,
        'count': len(results),
        'beaches': results
    })


@bp.route("/api/beaches", methods=['GET'])
def list_all_beaches():
    """Return all available beaches."""
    beaches = get_all_beaches()
    
    results = [
        {
            'name': beach['english_name'],
            'hebrew_name': beach['hebrew_name'],
            'lat': beach['latitude'],
            'lng': beach['longitude']
        }
        for beach in beaches
    ]
    
    return jsonify({
        'success': True,
        'count': len(results),
        'beaches': results
    })
