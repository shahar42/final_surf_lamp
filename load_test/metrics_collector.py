"""Custom metrics beyond Locust built-ins"""

# TODO: import numpy for percentile calculations

class MetricsCollector:
    """Aggregates response times and errors"""
    response_times = []
    error_counts = {}

    @classmethod
    def record_response_time(cls, response_time_ms):
        """Called from Locust event listener"""
        # TODO: cls.response_times.append(response_time_ms)
        pass

    @classmethod
    def calculate_percentiles(cls):
        """Compute p50, p95, p99"""
        # TODO: Use np.percentile()
        # TODO: Return dict with p50, p95, p99, mean, max
        pass

    @classmethod
    def save_results(cls):
        """Write JSON to results/{timestamp}_metrics.json"""
        # TODO: Build results dict
        # TODO: Write to file
        pass
