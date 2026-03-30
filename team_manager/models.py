from dataclasses import dataclass
from typing import Optional

@dataclass
class Worker:
    id: int
    name: str
    role: str
    tags: Optional[str] = None
    rating: int = 5
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None

@dataclass
class Contract:
    id: int
    worker_id: int
    title: str
    rate: str
    start_date: str
    payment_type: str = 'Monthly Salary'
    end_date: Optional[str] = None
    terms: Optional[str] = None
    status: str = 'Active'
    pdf_filename: Optional[str] = None
    # Optional field for joined queries
    worker_name: Optional[str] = None
