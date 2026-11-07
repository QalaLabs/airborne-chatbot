from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel

class StudentPersona(str, Enum):
    ASPIRING_BEGINNER = "aspiring_beginner"       # 10+2 / Arts / Commerce beginner exploring CPL
    GROUND_SCHOOL_CADET = "ground_school_cadet"   # Active student pilot preparing for DGCA Pariksha exams
    CONVERSION_PILOT = "conversion_pilot"         # Foreign license holder converting to DGCA CPL / ATPL

class StudentProfile(BaseModel):
    student_id: str
    persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET
    educational_background: Optional[str] = "science_pcm"
    preferred_language: Optional[str] = "english"
    last_updated: Optional[float] = None

PERSONA_LABELS = {
    StudentPersona.ASPIRING_BEGINNER: "10+2 Beginner / Arts & Commerce",
    StudentPersona.GROUND_SCHOOL_CADET: "DGCA Ground School Cadet",
    StudentPersona.CONVERSION_PILOT: "Foreign CPL Conversion / ATPL"
}
