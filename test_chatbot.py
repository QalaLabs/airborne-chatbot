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
        self.assertGreater(len(result["chips"]), 0)

    def test_fee_and_loan_query(self):
        result = ai_engine.answer_query("What is the fee for pilot training and do you have loan options?")
        self.assertIn("Fee Breakdown", result["answer"])
        self.assertIn("SBI", result["answer"])
        self.assertTrue(result["escalation"]["needed"])

    def test_dgca_syllabus_query(self):
        result = ai_engine.answer_query("What are the 5 DGCA subjects and passing marks?")
        self.assertTrue("DGCA" in result["answer"] or "Air Navigation" in result["answer"])

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
