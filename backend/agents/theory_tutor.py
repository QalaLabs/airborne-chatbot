import json
import os
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from backend.rag_pipeline import rag_pipeline
from backend.models.student_profile import StudentPersona
from backend.raptor_module import raptor_engine
from backend.agents.quiz_engine import quiz_engine

DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class TheoryTutorAgent:
    """
    Autonomous subagent specialized in resolving DGCA Ground School theoretical doubts
    across Air Navigation, Aviation Meteorology, Air Regulations, Technical General,
    and Radio Telephony.
    Integrates RAPTOR tree retrieval, syllabus breadcrumbs, and interactive Pariksha quizzes.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)

    def generate_with_gemini(self, question: str, context_chunks: List[Dict[str, Any]], persona: StudentPersona) -> Optional[str]:
        api_key = os.environ.get("GEMINI_API_KEY", self.api_key)
        if not api_key:
            return None

        formatted_context = "\n\n".join([
            f"--- [Textbook: {c['book_title']}, Page {c['page_number']}, Subject: {c['subject']}] ---\n{c['text']}"
            for c in context_chunks
        ])

        persona_guidance = (
            "The student is a beginner (10+2 / Arts / Commerce). Use clear physical analogies, intuitive intuition, and encourage them."
            if persona == StudentPersona.ASPIRING_BEGINNER else
            "The student is an active DGCA Ground School cadet preparing for Pariksha exams. Use rigorous DGCA terminology, exact formulas, and exam question traps."
            if persona == StudentPersona.GROUND_SCHOOL_CADET else
            "The student is converting a foreign license (FAA/EASA) to DGCA CPL. Highlight India-specific airspace regulations and composite exam nuances."
        )

        system_instruction = (
            "You are the Senior Flight Ground Instructor at Airborne Aviation Academy (DGCA Approved Pilot Training Institute).\n"
            f"Target Student Persona: {persona_guidance}\n\n"
            "Explain the student's doubt thoroughly, accurately, and professionally based strictly on the provided verified DGCA textbook excerpts.\n"
            "You MUST state at the beginning: '📖 **Referred Background Source Book:** [Book Title], Page [Number] ([Subject])'.\n"
            "Always cite textbook titles and page numbers in bold (e.g. **Oxford Aviation Academy: Meteorology, Page 135**).\n"
            "Use clear markdown headings, bullet points, and formulas where applicable."
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
            print(f"[Theory Tutor] Gemini API synthesis error: {e}")

        return None

    def answer_theory_query(self, message: str, persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET) -> Dict[str, Any]:
        """
        Retrieves verified textbook chunks and synthesizes an authoritative response
        complete with 'under_the_hood' metadata, syllabus breadcrumbs, and DGCA practice quiz.
        """
        rag_results = rag_pipeline.search(message, top_k=3)

        if not rag_results:
            return {
                "answer": (
                    f"Thank you for your question regarding **\"{message}\"**.\n\n"
                    "Our Chief Flying Instructor (CFI) and Ground School faculty are available to clarify this theoretical question in detail.\n\n"
                    "📖 **Referred Background Source:** DGCA Pilot Training Curriculum & Airborne Aviation Ground School Syllabus"
                ),
                "chips": ["DGCA 5 Subjects", "CPL Ground School", "Class 1 & 2 Medicals", "Talk to Ground Instructor"],
                "under_the_hood": {
                    "matched": False,
                    "confidence_score": 0.0,
                    "retrieval_method": "DGCA Syllabus Fallback",
                    "primary_book": "Airborne Aviation Ground Syllabus",
                    "page_number": None,
                    "subject": "General Aviation Ground Training",
                    "chunk_excerpt": "No direct textbook match above similarity threshold."
                }
            }

        top_chunk = rag_results[0]
        raw_score = top_chunk.get("score", 15.0)
        confidence = min(99.4, round(70.0 + min(29.0, raw_score * 1.5), 1))
        subj_cluster = raptor_engine.resolve_subject_cluster(message) or top_chunk["subject"]
        breadcrumb_info = raptor_engine.get_syllabus_breadcrumb(subj_cluster)

        # Check for interactive DGCA practice quiz
        quiz = quiz_engine.match_quiz_for_query(message, top_chunk["subject"])
        default_chips = ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"]
        quiz_chips = []
        quiz_block = ""
        if quiz:
            quiz_block = (
                f"\n\n---\n#### 🎯 **DGCA Pariksha Practice Question:**\n"
                f"**{quiz['question']}**\n\n"
            )
            for opt in quiz["options"]:
                quiz_block += f"- {opt}\n"
            quiz_block += "\n*(Click an option below to test your understanding!)*"
            quiz_chips = [
                f"Option {opt[0]}: {opt[3:30]}..." if len(opt) > 35 else f"Option {opt[0]}: {opt[3:]}"
                for opt in quiz["options"]
            ]

        # Try Gemini LLM generation if key is configured
        gemini_ans = self.generate_with_gemini(message, rag_results, persona)
        if gemini_ans:
            full_ans = gemini_ans + quiz_block
            return {
                "answer": full_ans,
                "chips": quiz_chips if quiz_chips else default_chips,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": confidence,
                    "retrieval_method": f"RAPTOR Hierarchical Tree ({subj_cluster}) + Gemini Flash",
                    "primary_book": top_chunk["book_title"],
                    "page_number": top_chunk["page_number"],
                    "subject": top_chunk["subject"],
                    "syllabus_breadcrumb": breadcrumb_info["breadcrumb"],
                    "recommended_next": breadcrumb_info["recommended_next"],
                    "chunk_excerpt": top_chunk["text"][:300].strip() + "..."
                }
            }

        # Offline Curated Structured Response Card
        sources_md = []
        citations = []
        for r in rag_results:
            source_tag = f"**{r['book_title']}** (Page {r['page_number']}) — *{r['subject']}*"
            citations.append(source_tag)
            clean_snippet = r['text'].strip()
            if len(clean_snippet) > 380:
                clean_snippet = clean_snippet[:380] + "..."
            sources_md.append(f"> 📖 **{r['book_title']} [p. {r['page_number']}]**:\n> \"{clean_snippet}\"")

        # Persona-tailored preamble
        persona_note = ""
        if persona == StudentPersona.ASPIRING_BEGINNER:
            persona_note = "> 💡 *Student Pilot Note: This concept forms a mandatory question in the DGCA CPL entrance and ground exams.*\n\n"
        elif persona == StudentPersona.CONVERSION_PILOT:
            persona_note = "> 💡 *License Conversion Note: Verified DGCA specification for Indian FIR compliance.*\n\n"

        answer_body = (
            f"### ✈️ **DGCA Textbook Doubt Resolution**\n\n"
            f"📖 **Referred Background Source Book:** **{top_chunk['book_title']}** (Page {top_chunk['page_number']}) — *Subject: {top_chunk['subject']}*\n\n"
            f"{persona_note}"
            f"Here is the verified theoretical explanation from the official **DGCA Aviation Syllabus & Curriculum**:\n\n"
            f"{top_chunk['text'].strip()}\n\n"
        )

        if len(rag_results) > 1:
            answer_body += "#### 🔍 Additional Technical References:\n" + "\n\n".join(sources_md[1:]) + "\n\n"

        answer_body += "📚 **Referenced DGCA Textbooks:**\n" + "\n".join([f"- {c}" for c in citations])
        answer_body += quiz_block

        return {
            "answer": answer_body,
            "chips": quiz_chips if quiz_chips else default_chips,
            "under_the_hood": {
                "matched": True,
                "confidence_score": confidence,
                "retrieval_method": f"RAPTOR Hierarchical Tree ({subj_cluster}) + FTS5 BM25",
                "primary_book": top_chunk["book_title"],
                "page_number": top_chunk["page_number"],
                "subject": top_chunk["subject"],
                "syllabus_breadcrumb": breadcrumb_info["breadcrumb"],
                "recommended_next": breadcrumb_info["recommended_next"],
                "chunk_excerpt": top_chunk["text"][:300].strip() + "..."
            }
        }
