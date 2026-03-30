FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy monitoring service files
COPY render_monitoring_service.py .
COPY surf_lamp_insights.py .
COPY render-mcp-server/ ./render-mcp-server/

# Create insights directory
RUN mkdir -p insights

CMD ["python", "render_monitoring_service.py"]