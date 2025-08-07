```python
from sqlalchemy import Column, Integer, String, JSON, UUID, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class LampRegistry(Base):
    __tablename__ = 'lamp_registry'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lamp_id = Column(String, unique=True, nullable=False)
    brightness = Column(Integer, nullable=False)
    location_used = Column(String, nullable=False)
    wave_height_m = Column(JSON, nullable=True)
    wave_period_s = Column(JSON, nullable=True)
    wind_speed_mps = Column(JSON, nullable=True)
    wind_deg = Column(JSON, nullable=True)
    registered = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<LampRegistry(id={self.id}, lamp_id={self.lamp_id}, brightness={self.brightness}, location_used={self.location_used})>"

class APIConfiguration(Base):
    __tablename__ = 'api_configuration'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key = Column(String, unique=True, nullable=False)
    api_url = Column(String, nullable=False)
    last_updated = Column(String, nullable=False)

    def __repr__(self):
        return f"<APIConfiguration(id={self.id}, api_key={self.api_key}, api_url={self.api_url}, last_updated={self.last_updated})>"

class SystemConfiguration(Base):
    __tablename__ = 'system_configuration'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_name = Column(String, unique=True, nullable=False)
    setting_value = Column(JSON, nullable=False)

    def __repr__(self):
        return f"<SystemConfiguration(id={self.id}, setting_name={self.setting_name}, setting_value={self.setting_value})>"

class ActivityLog(Base):
    __tablename__ = 'activity_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(String, nullable=False)
    log_level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, timestamp={self.timestamp}, log_level={self.log_level}, message={self.message})>"
```