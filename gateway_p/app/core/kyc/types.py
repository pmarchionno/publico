from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class KYCStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MORE_INFO_NEEDED = "MORE_INFO_NEEDED"

class IdentityData(BaseModel):
    first_name: str
    last_name: str
    dob: str
    national_id: str
    country: str

class VerificationResult(BaseModel):
    verification_id: str
    status: KYCStatus
    provider_reference: Optional[str] = None
    reason: Optional[str] = None
