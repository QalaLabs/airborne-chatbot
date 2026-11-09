import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path("data/aviation_rag.db")

class AviationSQLRAG:
    """
    Structured SQL-RAG Engine (EduBot Pattern).
    Executes high-precision read-only SQL queries over structured aviation tables:
    - dgca_exams: Exact passing percentages, exam codes, question counts, and portals
    - flying_hours_schedule: DGCA Rule 38A & Schedule II 200 hours mandatory distribution
    - course_fees_installments: Fee ranges, installment milestones, and fleet specs
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a strictly read-only SELECT query against the SQLite database"""
        clean_query = query.strip()
        if not clean_query.upper().startswith("SELECT"):
            raise ValueError("Only read-only SELECT queries are allowed in SQL-RAG.")

        with sqlite3.connect(str(self.db_path), timeout=15.0) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(clean_query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def query_exams_table(self) -> str:
        """Generates structured table for all DGCA theoretical examinations"""
        rows = self._execute_query("SELECT subject_code, subject_name, total_questions, pass_percentage, negative_marking, validity_years, exam_portal, frequency FROM dgca_exams")
        
        md = "### 📚 **DGCA Theoretical Ground Examinations (Pariksha CBT)**\n\n"
        md += "| Code | Subject | Format | Pass % | Negative Marking | Validity | Portal |\n"
        md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for r in rows:
            md += f"| **{r['subject_code']}** | {r['subject_name']} | {r['total_questions']} Qs | **{r['pass_percentage']}%** | {r['negative_marking']} | {r['validity_years']} Years | [{r['exam_portal']}](https://{r['exam_portal']}) |\n"
        
        md += "\n> 💡 *Exam Frequency: Conducted quarterly (every 3 months) by DGCA Central Examination Organisation.*\n\n"
        md += "📖 **Referred Background Source:** DGCA CAR Section 7, Series J Part I & Pariksha Examination Matrix ([pariksha.dgca.gov.in](https://pariksha.dgca.gov.in))"
        return md

    def query_flying_hours_table(self) -> str:
        """Generates structured table for DGCA 200 flying hours breakdown"""
        rows = self._execute_query("SELECT requirement_name, mandatory_hours, dgca_rule, aircraft_type, details FROM flying_hours_schedule")
        
        md = "### 🛩️ **DGCA CPL 200 Flying Hours Distribution Schedule**\n\n"
        md += "| Training Requirement | Minimum Hours | DGCA Statutory Rule | Aircraft / Sim |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for r in rows:
            md += f"| **{r['requirement_name']}** | **{r['mandatory_hours']} hrs** | {r['dgca_rule']} | {r['aircraft_type']} |\n"
        
        md += "\n#### 📋 Specific Syllabus Milestones:\n"
        for r in rows:
            if r['mandatory_hours'] < 200:
                md += f"- **{r['requirement_name']}**: {r['details']}\n"

        md += "\n📖 **Referred Background Source Book:** Air Regulations: RK Bali 15th Edition (DGCA Aircraft Rules 1937, Schedule II, Section J)"
        return md

    def query_course_comparison(self) -> str:
        """Generates structured course comparison matrix"""
        rows = self._execute_query("SELECT course_title, duration, fee_range_inr, installments_count, loan_eligible, key_fleet FROM course_fees_installments")
        
        md = "### ✈️ **Airborne Aviation Pilot Training Programs Comparison**\n\n"
        md += "| Course Program | Duration | Total Investment | Installments | Bank Loan | Primary Fleet |\n"
        md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for r in rows:
            loan_tag = "✅ Yes (SBI/HDFC)" if r['loan_eligible'] else "❌ Direct Pay"
            md += f"| **{r['course_title']}** | {r['duration']} | **{r['fee_range_inr']}** | {r['installments_count']} Stages | {loan_tag} | {r['key_fleet']} |\n"

        md += "\n> 💡 *All conventional CPL programs include 200 logged flying hours on Garmin G1000 glass cockpit Cessna 172 fleet.*\n\n"
        md += "📖 **Referred Background Source:** Airborne Aviation Academy Official Fee Matrix & DGCA Approved Flight Training Syllabus"
        return md

sql_rag = AviationSQLRAG()
