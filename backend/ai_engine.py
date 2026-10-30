import json
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from backend.rag_pipeline import rag_pipeline

DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# Comprehensive regex patterns for high-intent complex escalations
COMPLEX_PATTERNS = [
    re.compile(r'(loan|emi|financ|sbi|hdfc|bank)\b.*(approv|sanction|interest|amount|collateral|moratorium|lakh|crore)', re.I),
    re.compile(r'(approv|sanction|collateral)\b.*(loan|emi)', re.I),
    re.compile(r'(medical|doctor|vision|eyesight|color blind|lasik)\b.*(fail|reject|appeal|board|iam|afcme|pmr|fit)', re.I),
    re.compile(r'(fail|reject|appeal)\b.*(medical|class 1|class 2)', re.I),
    re.compile(r'cadet\b.*(interview|prep|indigo|air india|spicejet|adapt|compass|selection|assessment)', re.I),
    re.compile(r'(indigo|air india|spicejet)\b.*cadet', re.I),
    re.compile(r'(talk|speak|call|connect)\b.*(human|counselor|advisor|agent|person|instructor|desk|phone|whatsapp)', re.I),
    re.compile(r'(call|phone|whatsapp)\s*(me|now|back)', re.I),
    re.compile(r'(discount|concession|scholarship|negotiat|waiver|fee reduction)', re.I),
    re.compile(r'(foreign|faa|caa|sacaa|easa|conversion|convert)\b.*(license|cpl|dgca)', re.I)
]

# Core aviation terminology to guard against random false-positive RAG retrieval
AVIATION_TERMS = {
    "cpl", "ppl", "atpl", "dgca", "pilot", "plane", "aircraft", "flying", "flight",
    "nav", "navigation", "altimeter", "stall", "weather", "met", "meteorology",
    "qnh", "qfe", "engine", "airspace", "course", "fee", "fees", "medical", "class 1",
    "class 2", "rtr", "license", "cadet", "ground school", "speed", "knot", "runway",
    "atc", "cessna", "multi-engine", "instrument", "vor", "dme", "ils", "radar",
    "squawk", "fdtl", "cross country", "solo", "computer number", "egca", "pariksha",
    "aerodynamics", "lift", "drag", "thrust", "airframe", "hydraulics", "propeller",
    "monsoon", "turbulence", "icing", "cloud", "cumulonimbus", "metar", "taf",
    "cost", "price", "installment", "salary", "hours", "admission", "eligibility",
    "physics", "maths", "nios", "arts", "commerce", "12th", "spectacles", "glasses"
}

class AviationAIEngine:
    def __init__(self, kb_path: str = "backend/knowledge_base.json"):
        self.kb_path = kb_path
        self.kb = self._load_kb()
        self.api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)

    def _load_kb(self) -> Dict[str, Any]:
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_complex_query(self, message: str) -> tuple[bool, str]:
        """
        Detects if query requires escalation to human counselor / WhatsApp / Phone using flexible regex.
        Returns (is_complex, reason)
        """
        for pattern in COMPLEX_PATTERNS:
            if pattern.search(message):
                # Classify reason
                text = message.lower()
                if any(w in text for w in ["loan", "emi", "bank", "sbi", "hdfc", "financ"]):
                    return True, "Personalized Education Loan & Fee Assistance Required"
                elif any(w in text for w in ["medical", "appeal", "reject", "color", "vision", "specs", "lasik"]):
                    return True, "DGCA Medical Fitness & Medical Appeal Counseling Required"
                elif any(w in text for w in ["cadet", "adapt", "compass", "indigo", "interview"]):
                    return True, "Airline Cadet Pilot Selection & Assessment Consultation"
                elif any(w in text for w in ["discount", "concession", "scholarship", "waiver"]):
                    return True, "Scholarship & Fee Concession Desk"
                elif any(w in text for w in ["foreign", "conversion", "faa"]):
                    return True, "License Conversion & Eligibility Evaluation Required"
                else:
                    return True, "Direct request to connect with Senior Flight Advisor"

        return False, ""

    def is_adversarial_or_jailbreak(self, message: str) -> bool:
        """Detect prompt injection and system jailbreak attempts"""
        lower = message.lower()
        jailbreak_triggers = [
            "ignore all previous", "ignore previous instructions", "forget your instructions",
            "you are no longer", "system prompt", "print your prompt", "leak your prompt",
            "act as a", "pretend you are", "jailbreak", "DAN mode", "bypass"
        ]
        return any(t in lower for t in jailbreak_triggers)

    def is_aviation_query(self, message: str) -> bool:
        """Determines if query belongs to the aviation domain"""
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', message.lower()))
        if tokens & AVIATION_TERMS:
            return True
        # Check partial stems for Hindi/Hinglish (e.g. pilot, udaan, jahaj, hawai)
        if any(w in message.lower() for w in ["pilot", "jahaj", "plane", "udaan", "cpl", "fees", "flight"]):
            return True
        return False

    def generate_escalation_data(self, query: str, reason: str) -> Dict[str, Any]:
        academy = self.kb.get("academy", {})
        wa_number = academy.get("whatsapp_number", "+919876543210").replace("+", "").replace(" ", "")
        
        prefilled_msg = f"Hi Airborne Aviation Academy! I am inquiring about: {query[:80]}... Please connect me with a senior flight training counselor."
        encoded_msg = urllib.parse.quote(prefilled_msg)
        wa_url = f"https://wa.me/{wa_number}?text={encoded_msg}"

        return {
            "needed": True,
            "reason": reason,
            "whatsapp_url": wa_url,
            "whatsapp_display": academy.get("whatsapp_display", "+91 98765 43210"),
            "phone_helpline": academy.get("phone_helpline", "+91 1800 247 2676"),
            "alternate_phone": academy.get("alternate_phone", "+91 98765 43210"),
            "email": academy.get("email", "admissions@airborne-aviation.edu")
        }

    def generate_with_gemini(self, question: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
        """Calls Gemini Flash REST API with retrieved DGCA textbook excerpts"""
        api_key = os.environ.get("GEMINI_API_KEY", self.api_key)
        if not api_key:
            return None

        formatted_context = "\n\n".join([
            f"--- [Textbook: {c['book_title']}, Page {c['page_number']}, Subject: {c['subject']}] ---\n{c['text']}"
            for c in context_chunks
        ])

        system_instruction = (
            "You are the Senior Flight Ground Instructor at Airborne Aviation Academy (DGCA Approved Pilot Training Institute). "
            "A student pilot has asked a question. Explain it thoroughly, accurately, and professionally based on the provided verified DGCA textbook excerpts. "
            "Always cite the textbook title and page numbers in bold (e.g. **Oxford Aviation Academy: Meteorology, Page 135**). "
            "Use clear markdown headings, bullet points, and formulas where applicable. "
            "If the question is in Hindi or Hinglish, answer in polite, clear Hinglish."
        )

        user_prompt = f"{system_instruction}\n\nStudent Question: {question}\n\nVerified DGCA Textbook Excerpts:\n{formatted_context}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
        }

        try:
            req = urllib.request.Request(
                GEMINI_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as e:
            print(f"[AI Engine] Gemini API error: {e}")

        return None

    def answer_query(self, message: str) -> Dict[str, Any]:
        """Processes student query with scope guardrails, RAG, and escalation"""
        text = message.strip()
        is_complex, complex_reason = self.is_complex_query(text)
        escalation = self.generate_escalation_data(message, complex_reason) if is_complex else {
            "needed": False,
            "whatsapp_url": f"https://wa.me/{self.kb['academy']['whatsapp_number'].replace('+', '')}",
            "whatsapp_display": self.kb["academy"]["whatsapp_display"],
            "phone_helpline": self.kb["academy"]["phone_helpline"]
        }

        # 1. Adversarial & Jailbreak Defense
        if self.is_adversarial_or_jailbreak(text):
            return {
                "answer": (
                    "### 🛡️ **Airborne Flight Training Assistant**\n\n"
                    "I am the dedicated 24/7 AI Flight Training Advisor for **Airborne Aviation Academy**. "
                    "My operating guidelines restrict me exclusively to DGCA flight training, ground school subjects, CPL/ATPL course fees, and pilot career counseling. "
                    "How can I assist your aviation and flight training journey today?"
                ),
                "chips": ["DGCA CPL Syllabus", "Course Fee Breakdown", "Class 1 & 2 Medicals", "Bank Loan Assistance"],
                "escalation": escalation
            }

        # 2. Greetings
        if any(w in text.lower() for w in ["hello", "hi", "hey", "good morning", "good evening", "namaste", "start"]):
            response_text = (
                f"### Welcome to **{self.kb['academy']['name']}**! ✈️\n\n"
                "I am your **24/7 AI Aviation Flight Advisor & Ground School Tutor**, powered by **Gemini Flash & 13 DGCA Pilot Training Textbooks (9,200+ knowledge chunks)**. "
                "I can resolve every doubt regarding:\n\n"
                "- 📚 **DGCA Ground Subjects:** Air Navigation, Meteorology, Regulations, Technical General/Specific & RTR(A)\n"
                "- 💰 **Fee Structures & 100% Bank Loan Tie-ups**\n"
                "- 🩺 **Class 1 & Class 2 Medicals, Eye Vision & Computer Number**\n"
                "- 🛩️ **CPL 200 Flying Hours & Cadet Pilot Programs**\n\n"
                "Ask any theoretical doubt or select a quick topic below!"
            )
            chips = [
                "Commercial Pilot Course (CPL)",
                "Full Fee Structure & Loans",
                "DGCA Syllabus & Exams",
                "Class 1 & 2 Medical Process",
                "Aerodynamic Stall & Lift"
            ]
            return {"answer": response_text, "chips": chips, "escalation": escalation}

        # 3. Fee & Loan queries
        if any(w in text.lower() for w in ["fee", "fees", "cost", "price", "budget", "expensive", "charges", "installment", "sbi", "hdfc"]):
            budget = self.kb["fees_and_loans"]["budget_summary"]
            loans = self.kb["fees_and_loans"]["bank_loans"]
            response_text = (
                "### 💰 **Comprehensive Pilot Training Fee Breakdown**\n\n"
                "Becoming a Commercial Pilot in India involves the following cost components:\n\n"
                "| Component | Estimated Cost | Notes |\n"
                "| :--- | :--- | :--- |\n"
                f"| **DGCA Ground School** | {budget['ground_school']} | 5 subjects + RTR(A) exam prep |\n"
                f"| **200 Flying Hours (India)** | {budget['flying_training_200hrs']} | Cessna 172 Glass Cockpit + Multi-Engine |\n"
                f"| **Medicals & DGCA Exam Fees** | {budget['dgca_exam_and_medical_fees']} | Class 2, Class 1 & 5 DGCA papers |\n"
                f"| **Books, Uniform & Headset** | {budget['uniform_books_navigation_logbook']} | Navigation computer, logbook, charts |\n"
                f"| **Total Conventional CPL** | **{budget['total_estimated_conventional_cpl']}** | Payable in 4-5 stage installments |\n\n"
                "#### 🏦 **Education Loans & Financing**:\n"
                f"- **Partner Banks**: {', '.join(loans['partner_banks'])}\n"
                f"- **Loan Coverage**: Up to ₹1.5 Cr with approved collateral; up to ₹7.5 Lakhs collateral-free under national education schemes.\n"
                f"- **Moratorium Period**: {loans['moratorium']}\n"
                f"- **Interest Rate**: Typically {loans['interest_rate_range']}.\n\n"
                "> 💡 *Tip: We provide bonafide fee structure certificates and quotation letters required by banks for instant loan sanctions.*"
            )
            chips = ["CPL Installment Schedule", "Bank Loan Assistance", "Cadet Pilot Costs", "Talk to Finance Counselor"]
            escalation["needed"] = True
            escalation["reason"] = "Personalized Loan & Installment Consultation Available"
            return {"answer": response_text, "chips": chips, "escalation": escalation}

        # 4. Out-of-Domain Guardrail: Rejection of non-aviation requests (recipes, coding hacks, stocks)
        if not self.is_aviation_query(text) and not is_complex:
            return {
                "answer": (
                    "### ✈️ **Airborne Aviation Academy Assistant**\n\n"
                    "I specialize strictly in **DGCA Pilot Training & Aviation Ground School** (Air Navigation, Aviation Meteorology, Air Regulations, Technical General, and RTR-A).\n\n"
                    "I cannot assist with unrelated queries like general programming, cooking recipes, or stock market trading.\n\n"
                    "Please feel free to ask any question regarding:\n"
                    "- 🛫 **CPL & Airline Cadet Pilot Programs**\n"
                    "- 📚 **DGCA Ground Exam Subjects & Theory Doubts**\n"
                    "- 💰 **Flight Training Fees & Bank Loan Tie-ups**\n"
                    "- 🩺 **Class 1 & Class 2 Medicals and Vision Rules**"
                ),
                "chips": ["CPL Course Details", "DGCA 5 Subjects", "Total Course Cost", "Class 1 & 2 Medicals"],
                "escalation": escalation
            }

        # 5. Search the RAG Database across all 13 DGCA Books
        rag_results = rag_pipeline.search(message, top_k=3)

        if rag_results:
            # Try Gemini synthesis
            gemini_ans = self.generate_with_gemini(message, rag_results)
            if gemini_ans:
                return {
                    "answer": gemini_ans,
                    "chips": ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"],
                    "escalation": escalation
                }

            # Local RAG fallback
            sources_md = []
            citations = []
            for r in rag_results:
                source_tag = f"**{r['book_title']}** (Page {r['page_number']}) — *{r['subject']}*"
                citations.append(source_tag)
                clean_snippet = r['text'].strip()
                if len(clean_snippet) > 450:
                    clean_snippet = clean_snippet[:450] + "..."
                sources_md.append(f"> 📖 **{r['book_title']} [p. {r['page_number']}]**:\n> \"{clean_snippet}\"")

            answer_body = (
                f"### ✈️ **DGCA Textbook Doubt Resolution**\n\n"
                f"Here is the verified theoretical explanation from the official **DGCA Aviation Syllabus & Curriculum**:\n\n"
                f"{rag_results[0]['text'].strip()}\n\n"
            )

            if len(rag_results) > 1:
                answer_body += f"#### 🔍 Additional Technical References:\n" + "\n\n".join(sources_md[1:]) + "\n\n"

            answer_body += f"📚 **Referenced DGCA Textbooks:**\n" + "\n".join([f"- {c}" for c in citations])

            chips = ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"]
            return {"answer": answer_body, "chips": chips, "escalation": escalation}

        # 6. Default fallback for general aviation queries
        escalation["needed"] = True
        escalation["reason"] = "Aviation advisor ready to answer your specific flight question"
        response_text = (
            f"Thank you for your question regarding **\"{message}\"**.\n\n"
            "At **Airborne Aviation Academy**, our flight training instructors and admissions counselors are on standby 24/7 to resolve every query about:\n\n"
            "- ✈️ **CPL Flying Hours & Multi-Engine Endorsements**\n"
            "- 💰 **Fee Schedules, EMI Options & Bank Education Loans**\n"
            "- 📚 **DGCA Computer Number, eGCA Verification & Exam Syllabus**\n"
            "- 🩺 **Class 1 & Class 2 Medicals and Vision Clearances**\n"
            "- 👨‍✈️ **Airline Recruitment & Cadet Pilot Programs**\n\n"
            "To get immediate personalized guidance, connect directly with our Senior Flight Advisor below via WhatsApp or call our 24/7 toll-free helpline."
        )
        chips = ["CPL Course Details", "Fee Structure & Loans", "DGCA Syllabus", "Class 1 & 2 Medicals", "Chat on WhatsApp"]
        return {"answer": response_text, "chips": chips, "escalation": escalation}

ai_engine = AviationAIEngine()
