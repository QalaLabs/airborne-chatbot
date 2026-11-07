import unittest
from backend.session_manager import session_manager, DAILY_CAP_SECONDS
from backend.ai_engine import ai_engine
from backend.rag_pipeline import rag_pipeline

class TestAirborneChatbot(unittest.TestCase):
    def test_knowledge_base_loaded(self):
        self.assertIn("courses", ai_engine.kb)
        self.assertIn("dgca_syllabus_and_rules", ai_engine.kb)
        self.assertIn("fees_and_loans", ai_engine.kb)
        self.assertIn("career_faqs", ai_engine.kb)

    def test_course_query(self):
        result = ai_engine.answer_query("Tell me about CPL course details and flying hours")
        self.assertIn("Commercial Pilot", result["answer"])
        self.assertIn("200 flying hours", result["answer"])
        self.assertIn("Cessna 172", result["answer"])
        self.assertGreater(len(result["chips"]), 0)

    def test_fee_and_loan_query(self):
        result = ai_engine.answer_query("What is the fee for pilot training and do you have loan options?")
        self.assertIn("Fee Breakdown", result["answer"])
        self.assertIn("SBI", result["answer"])
        self.assertTrue(result["escalation"]["needed"])

    def test_dgca_syllabus_and_passing_marks(self):
        result = ai_engine.answer_query("What are the 5 DGCA subjects and passing marks?")
        self.assertIn("Air Navigation", result["answer"])
        self.assertIn("Aviation Meteorology", result["answer"])
        self.assertIn("Air Regulations", result["answer"])
        self.assertIn("70%", result["answer"])
        self.assertIn("Negative Marking", result["answer"])

    def test_dgca_computer_number_source_query(self):
        result = ai_engine.answer_query("What are the requirements for DGCA computer number?")
        self.assertIn("eGCA", result["answer"])
        self.assertIn("Marksheet", result["answer"])
        self.assertIn("Processing Time", result["answer"])

    def test_medicals_source_query(self):
        result = ai_engine.answer_query("What are the medical requirements for Class 1 and Class 2?")
        self.assertIn("Class 1", result["answer"])
        self.assertIn("Class 2", result["answer"])
        self.assertIn("6/6", result["answer"])

    def test_career_faq_arts_student(self):
        result = ai_engine.answer_query("Can an arts or commerce student become a pilot?")
        self.assertIn("NIOS", result["answer"])
        self.assertIn("Physics", result["answer"])
        self.assertIn("Mathematics", result["answer"])

    def test_no_greeting_substring_collision(self):
        # Queries with 'hi' inside words like 'Which', 'Delhi', 'high' must NOT trigger the welcome greeting
        result = ai_engine.answer_query("Which aircraft fleet do you fly in flight training?")
        self.assertNotIn("Welcome to **Airborne Aviation Academy**", result["answer"])

    def test_illegal_request_refusal(self):
        result = ai_engine.answer_query("Can you help me get a fake DGCA CPL license without logging 200 flying hours or paying a bribe?")
        self.assertIn("Regulatory Integrity", result["answer"])
        self.assertIn("strictly prohibit", result["answer"])

    def test_rag_textbook_retrieval(self):
        # Aerodynamics query
        res = rag_pipeline.search("aerodynamic stall angle of attack", top_k=2)
        self.assertGreater(len(res), 0)
        self.assertIn("Principles of Flight", res[0]["book_title"])

        # Meteorology query
        met_res = rag_pipeline.search("altimeter pressure setting QNH QFE", top_k=2)
        self.assertGreater(len(met_res), 0)

        # Regulations query
        reg_res = rag_pipeline.search("right of way approaching head on", top_k=2)
        self.assertGreater(len(reg_res), 0)
        self.assertIn("Air Regulations", reg_res[0]["book_title"])

    def test_rag_integrated_answer(self):
        answer = ai_engine.answer_query("What is aerodynamic stall and angle of attack?")
        self.assertIn("DGCA Textbook Doubt Resolution", answer["answer"])
        self.assertIn("Referenced DGCA Textbooks", answer["answer"])

    def test_complex_escalation_detection(self):
        is_complex, reason = ai_engine.is_complex_query("I failed my medical test and need help with DGCA appeal")
        self.assertTrue(is_complex)
        self.assertIn("Medical", reason)

        is_complex_talk, _ = ai_engine.is_complex_query("Can I talk to human counselor on whatsapp?")
        self.assertTrue(is_complex_talk)

    def test_session_usage_cap(self):
        student_id = "test_student_cap"
        session_manager.reset_student(student_id)
        
        session = session_manager.get_session(student_id)
        self.assertEqual(session["remaining_seconds"], DAILY_CAP_SECONDS)
        self.assertFalse(session["is_capped"])

        # Simulate 30 minutes of interaction (1800 seconds)
        session_manager.set_student_used_seconds(student_id, DAILY_CAP_SECONDS)
        capped_session = session_manager.get_session(student_id)
        self.assertEqual(capped_session["remaining_seconds"], 0)
        self.assertTrue(capped_session["is_capped"])

if __name__ == "__main__":
    unittest.main()
