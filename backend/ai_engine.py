import json
import os
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from backend.rag_pipeline import rag_pipeline

# Try importing google-generativeai for Gemini support
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class AviationAIEngine:
    def __init__(self, kb_path: str = "backend/knowledge_base.json"):
        self.kb_path = kb_path
        self.kb = self._load_kb()
        self.gemini_model = None
        self._init_gemini()

    def _load_kb(self) -> Dict[str, Any]:
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_gemini(self):
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if HAS_GENAI and gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=(
                        "You are the Senior Flight Ground Instructor and 24/7 Aviation AI Assistant for Airborne Aviation Academy (DGCA Approved). "
                        "Answer student flight training and DGCA examination questions accurately, professionally, and clearly. "
                        "When provided with verified textbook excerpts from DGCA syllabus books, base your explanations directly on that evidence and cite the textbook title and page numbers. "
                        "Maintain a supportive, authoritative tone suitable for aspiring airline pilots."
                    )
                )
                print("[AI Engine] Google Gemini 1.5 Flash initialized successfully.")
            except Exception as e:
                print(f"[AI Engine] Could not initialize Gemini: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None

    def is_complex_query(self, message: str) -> tuple[bool, str]:
        """
        Detects if query requires escalation to human counselor / WhatsApp / Phone.
        Returns (is_complex, reason)
        """
        text = message.lower()
        
        # Explicit request for human
        if any(w in text for w in ["talk to human", "speak to human", "human agent", "counselor", "call me", "phone number", "contact person", "whatsapp me", "talk to someone", "callback"]):
            return True, "Direct request to connect with Senior Flight Advisor"

        # Financial / Loan approvals / discounts
        if any(w in text for w in ["loan approval", "sanction letter", "collateral", "discount", "fee concession", "scholarship", "custom installment", "negotiate"]):
            return True, "Personalized Education Loan & Fee Assistance Required"

        # Medical issues / appeals / rejections
        if any(w in text for w in ["failed medical", "medical rejection", "appeal", "dgca appeal", "color blind", "lasik rejected", "pmr issue", "asthma", "heart"]):
            return True, "DGCA Medical Fitness & Medical Appeal Counseling Required"

        # Cadet program selection / interview prep
        if any(w in text for w in ["cadet interview", "airline exam dates", "compass test", "adapt assessment", "cadet letter of intent"]):
            return True, "Airline Cadet Pilot Selection & Assessment Consultation"

        # Complex non-science or degree conversion queries
        if any(w in text for w in ["foreign license conversion", "faa to dgca", "caa to dgca", "sacaa to dgca", "dropped out", "failed 12th"]):
            return True, "License Conversion & Eligibility Evaluation Required"

        return False, ""

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

    def answer_query(self, message: str) -> Dict[str, Any]:
        """
        Processes query against knowledge base and 13 DGCA Books RAG database.
        Uses Gemini if configured, otherwise falls back to verified RAG engine.
        """
        text = message.strip().lower()
        is_complex, complex_reason = self.is_complex_query(text)
        escalation = self.generate_escalation_data(message, complex_reason) if is_complex else {
            "needed": False,
            "whatsapp_url": f"https://wa.me/{self.kb['academy']['whatsapp_number'].replace('+', '')}",
            "whatsapp_display": self.kb["academy"]["whatsapp_display"],
            "phone_helpline": self.kb["academy"]["phone_helpline"]
        }

        # 1. Greetings
        if any(w in text for w in ["hello", "hi", "hey", "good morning", "good evening", "namaste", "start"]):
            response_text = (
                f"### Welcome to **{self.kb['academy']['name']}**! ✈️\n\n"
                "I am your **24/7 AI Aviation Flight Advisor & Ground School Tutor**, backed by **13 DGCA Pilot Training Textbooks (9,200+ knowledge chunks)**. "
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
            return {
                "answer": response_text,
                "chips": chips,
                "escalation": escalation
            }

        # 2. Fee & Loan queries
        if any(w in text for w in ["fee", "fees", "cost", "price", "budget", "expensive", "charges", "installment", "sbi", "hdfc"]):
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
            return {
                "answer": response_text,
                "chips": chips,
                "escalation": escalation
            }

        # 3. Medicals (Class 1 & Class 2)
        if any(w in text for w in ["medical", "medicals", "class 1", "class 2", "eyesight", "eye", "vision", "specs", "glasses", "lasik", "afcme", "iam"]):
            c2 = self.kb["dgca_syllabus_and_rules"]["medicals"]["class_2"]
            c1 = self.kb["dgca_syllabus_and_rules"]["medicals"]["class_1"]
            response_text = (
                "### 🩺 **DGCA Medical Examination Roadmap**\n\n"
                "To fly as a commercial pilot in India, you must clear two medical stages:\n\n"
                "#### 1️⃣ **DGCA Class 2 Medical (First Step)**\n"
                f"- **Conducted By**: DGCA-Empanelled Class 2 Civil Doctors.\n"
                f"- **Tests**: {c2['tests_included']}\n"
                f"- **Validity**: {c2['validity']}\n"
                "- **Cost**: Approx. ₹5,000 - ₹8,000 paid directly to the clinic/diagnostic labs.\n"
                "- **Outcome**: Fit Certificate issued; doctor forwards file to DGCA Medical Cell to generate your **Permanent Medical Record (PMR) File Number**.\n\n"
                "#### 2️⃣ **DGCA Class 1 Medical (Final CPL Requirement)**\n"
                f"- **Conducted By**: Premier IAF Centres — {', '.join(c1['authorized_centers'][:2])} & authorized civil centers.\n"
                f"- **Prerequisite**: Must have completed Class 2 with an active PMR number.\n"
                f"- **Vision Standard**: {c1['vision_criteria']}\n\n"
                "#### 👓 **Glasses & Lasik FAQ**:\n"
                "- **Spectacles**: Yes, up to standard refractive limits is allowed provided corrected vision is **6/6**.\n"
                "- **Lasik Surgery**: Allowed if completed after age 18 and minimum 6 months have elapsed with proven corneal stability."
            )
            chips = ["DGCA Empanelled Doctors List", "Apply for Computer Number", "PMR File Tracking", "Schedule Medical Guidance"]
            return {
                "answer": response_text,
                "chips": chips,
                "escalation": escalation
            }

        # 4. Search the RAG Database across all 13 DGCA Books
        rag_results = rag_pipeline.search(message, top_k=3)

        if rag_results:
            # Check if Gemini LLM is enabled
            if self.gemini_model:
                try:
                    context_chunks = "\n\n".join([
                        f"[Source: {r['book_title']}, Page {r['page_number']}, Subject: {r['subject']}]\n{r['text']}"
                        for r in rag_results
                    ])
                    llm_prompt = f"Student Question: {message}\n\nVerified DGCA Textbook Extracts:\n{context_chunks}\n\nProvide a comprehensive, clear, step-by-step flight instructor answer grounded in these extracts, citing the textbook and page number."
                    gemini_response = self.gemini_model.generate_content(llm_prompt)
                    if gemini_response and gemini_response.text:
                        return {
                            "answer": gemini_response.text,
                            "chips": ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"],
                            "escalation": escalation
                        }
                except Exception as e:
                    print(f"[AI Engine] Gemini generation fallback to local RAG: {e}")

            # Local High-Fidelity RAG fallback
            sources_md = []
            citations = []

            for idx, r in enumerate(rag_results):
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

            answer_body += (
                f"📚 **Referenced DGCA Textbooks:**\n"
                + "\n".join([f"- {c}" for c in citations])
            )

            chips = [
                "Explain Further",
                "Related DGCA Question",
                "Connect with Ground Instructor",
                "CPL Course Details"
            ]

            return {
                "answer": answer_body,
                "chips": chips,
                "escalation": escalation
            }

        # 5. Default fallback to general aviation knowledge base
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
        chips = [
            "CPL Course Details",
            "Fee Structure & Loans",
            "DGCA Syllabus",
            "Class 1 & 2 Medicals",
            "Chat on WhatsApp"
        ]
        return {
            "answer": response_text,
            "chips": chips,
            "escalation": escalation
        }

ai_engine = AviationAIEngine()
