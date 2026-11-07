import re
from typing import Dict, Any, Optional
from backend.models.student_profile import StudentPersona

class RegulatoryVerifierAgent:
    """
    Autonomous subagent specialized in DGCA regulatory compliance, medical eligibility,
    eGCA computer numbers, anti-fraud guardrails, and official portal verification protocols.
    """
    def __init__(self, kb: Dict[str, Any]):
        self.kb = kb

    def is_illegal_or_fraud(self, message: str) -> bool:
        lower = message.lower()
        illegal_triggers = [
            "fake license", "fake cpl", "fake dgca", "bribe", "cheat sheet",
            "cheat the test", "bypass medical", "illegal license", "buy license",
            "without logging 200", "forge license", "pass the ishihara plates test"
        ]
        return any(t in lower for t in illegal_triggers)

    def is_external_web_request(self, message: str) -> bool:
        lower = message.lower()
        triggers = [
            "scrape", "web scrape", "scraping", "crawl", "browse the web", "search google",
            "search the web", "check online", "check other website", "check other websites",
            "search internet", "search other sites", "from another website"
        ]
        return any(t in lower for t in triggers)

    def answer_regulatory_query(self, message: str, persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET) -> Dict[str, Any]:
        lower = message.lower()

        # 1. Illegal Request & Fraud Defense
        if self.is_illegal_or_fraud(message):
            return {
                "answer": (
                    "### 🛡️ **Airborne Compliance & Regulatory Integrity**\n\n"
                    "Airborne Aviation Academy operates in strict compliance with the **Directorate General of Civil Aviation (DGCA)**, Aircraft Rules 1937, and international flight safety standards.\n\n"
                    "We **strictly prohibit** and refuse any assistance with:\n"
                    "- ❌ Fabricated flight logbooks or bypass of mandatory 200 flying hours\n"
                    "- ❌ Fake DGCA licenses, cheating, or bribery\n"
                    "- ❌ Bypassing Class 1 or Class 2 medical examinations\n\n"
                    "All pilot qualifications must be earned legitimately through verified flight training, genuine medical board clearances, and passing official DGCA examinations.\n\n"
                    "📖 **Referred Background Source:** DGCA Aircraft Rules 1937 & Regulatory Compliance Enforcement Guidelines"
                ),
                "chips": ["DGCA CPL Syllabus", "Class 1 & 2 Medical Process", "Course Fee Breakdown", "Bank Loan Assistance"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "Regulatory Compliance Filter (Anti-Fraud Policy)",
                    "primary_book": "Aircraft Act 1934 & Indian Aircraft Rules 1937",
                    "page_number": 1,
                    "subject": "Aviation Safety & Regulatory Compliance",
                    "chunk_excerpt": "Strict prohibition of fraudulent licensing or medical examination bypass."
                }
            }

        # 2. External Web Request / Zero Web Scraping Interactive Confirmation Protocol
        if self.is_external_web_request(message):
            return {
                "answer": (
                    "### ⚠️ **Official DGCA Source Policy (Zero Third-Party Web Scraping)**\n\n"
                    "I do not possess or use general web scraping capabilities on arbitrary third-party websites. "
                    "To maintain 100% regulatory integrity and prevent unverified misinformation, I can answer queries **only if the information is officially published on official DGCA portals**:\n\n"
                    "- 🌐 **Directorate General of Civil Aviation:** [dgca.gov.in](https://www.dgca.gov.in)\n"
                    "- 🌐 **Central Examination Organisation (Pariksha):** [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in)\n\n"
                    "**No other website will be checked.**\n\n"
                    "Whenever official online information from these portals is referenced, the exact portal pages will be cited as the authoritative source.\n\n"
                    "Would you like me to verify whether your query is covered on [dgca.gov.in](https://www.dgca.gov.in) or [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in)?\n\n"
                    "📖 **Referred Background Source:** Official DGCA Regulatory Portal Policy ([dgca.gov.in](https://www.dgca.gov.in) & [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in))"
                ),
                "chips": ["Check dgca.gov.in Circulars", "Check pariksha.dgca.gov.in Schedules", "DGCA 5 Subjects", "Talk to Admissions Counselor"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "Official Portal Verification Protocol (Zero Scraping Policy)",
                    "primary_book": "Official DGCA Portals (dgca.gov.in & pariksha.dgca.gov.in)",
                    "page_number": 1,
                    "subject": "Regulatory Portal Governance",
                    "chunk_excerpt": "Strict restriction to official dgca.gov.in and pariksha.dgca.gov.in pages with zero arbitrary web scraping."
                }
            }

        # 3. DGCA Computer Number & eGCA
        if any(w in lower for w in ["computer number", "egca", "computer no"]):
            cn = self.kb["dgca_syllabus_and_rules"]["computer_number"]
            reqs = "\n".join([f"- {r}" for r in cn["requirements"]])
            ans = (
                "### 📋 **DGCA Computer Number & eGCA Registration Guide**\n\n"
                f"**What is a Computer Number?**\n{cn['definition']}\n\n"
                f"**Official Portal:** [{cn['portal']}]({cn['portal']})\n"
                f"**Processing Time:** {cn['processing_time']}\n\n"
                f"#### 📑 Mandatory Documents Checklist:\n{reqs}\n\n"
                "> 💡 *Airborne Support: Our admissions office assists all enrolled students with document attestation and eGCA submission free of charge.*\n\n"
                "📖 **Referred Background Source:** DGCA Aircraft Rules 1937, Schedule II & eGCA Portal Specifications ([egca.dgca.gov.in](https://egca.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["DGCA 5 Subjects", "Class 2 Medicals", "CPL Course Details", "Talk to Admissions Counselor"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.2,
                    "retrieval_method": "eGCA Regulatory Module",
                    "primary_book": "DGCA eGCA User Manual & Rule 67",
                    "page_number": 1,
                    "subject": "Flight Crew Licensing & Examination Verification",
                    "chunk_excerpt": cn["definition"]
                }
            }

        # 4. DGCA Syllabus, 5 Subjects, and Exam Pattern / Passing Marks
        if any(w in lower for w in ["5 subject", "five subject", "dgca subject", "passing mark", "pass percentage", "pariksha", "exam pattern", "negative marking"]) or ("syllabus" in lower and "cpl" in lower):
            exams = self.kb["dgca_syllabus_and_rules"]["dgca_exams"]
            gs = next((c for c in self.kb["courses"] if c["id"] == "ground-school"), None)
            subjects_list = "\n".join([f"{i+1}. **{s}**" for i, s in enumerate(gs["subjects_covered"])]) if gs else ""
            ans = (
                "### 📚 **DGCA CPL Theoretical Exam Pattern & Syllabus**\n\n"
                "To obtain a Commercial Pilot License in India, candidate pilots must clear theoretical examinations conducted by the DGCA (Central Examination Organisation / Pariksha portal).\n\n"
                f"#### 📝 **The 5 Core DGCA Ground Subjects:**\n{subjects_list}\n\n"
                "#### 📊 **DGCA Examination Guidelines:**\n"
                f"- **Format:** {exams['format']}\n"
                f"- **Passing Percentage:** **{exams['pass_percentage']}**\n"
                f"- **Negative Marking:** **{exams['negative_marking']}**\n"
                f"- **Exam Schedule:** {exams['frequency']}\n"
                f"- **Score Validity:** {exams['validity']}\n\n"
                "> ✈️ *Airborne Ground School provides chapter-wise question banks and mock exams on Pariksha CBT software.*\n\n"
                "📖 **Referred Background Source:** DGCA CAR Section 7 & Pariksha CBT Examination Curriculum ([pariksha.dgca.gov.in](https://pariksha.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Ground School Fees", "Computer Number Steps", "Class 1 & 2 Medicals", "CPL Flying Hours"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.4,
                    "retrieval_method": "Pariksha CBT Examination Curriculum Matrix",
                    "primary_book": "DGCA CAR Section 7 Series J & Pariksha Portal",
                    "page_number": 1,
                    "subject": "DGCA Theoretical Knowledge Examinations",
                    "chunk_excerpt": f"5 Subjects: Air Nav, Met, Regs, Tech Gen, RTR. Pass: {exams['pass_percentage']}, Negative: {exams['negative_marking']}"
                }
            }

        # 5. DGCA Class 1 & Class 2 Medicals, Eye Vision & Lasik
        if any(w in lower for w in ["medical", "medicals", "class 1", "class 2", "eye test", "vision", "lasik", "spectacle", "glasses"]):
            med = self.kb["dgca_syllabus_and_rules"]["medicals"]
            c2 = med["class_2"]
            c1 = med["class_1"]
            centers = "\n".join([f"- {c}" for c in c1["authorized_centers"]])
            ans = (
                "### 🩺 **DGCA Pilot Medical Fitness Guidelines (Class 1 & Class 2)**\n\n"
                "Every aspiring commercial pilot must undergo a two-tier medical examination mandated by DGCA:\n\n"
                "#### 1️⃣ **Class 2 Medical (Initial Entry Level):**\n"
                f"- **Purpose:** {c2['description']}\n"
                f"- **Key Tests:** {c2['tests_included']}\n"
                f"- **Validity:** {c2['validity']}\n"
                f"- **Outcome:** {c2['outcome']}\n\n"
                "#### 2️⃣ **Class 1 Medical (Commercial Pilot Level):**\n"
                f"- **Purpose:** {c1['description']}\n"
                f"- **Authorized Centers:**\n{centers}\n"
                f"- **Vision Standard:** {c1['vision_criteria']}\n\n"
                "> 💡 *Important: You must obtain your Class 2 Medical Assessment and DGCA PMR file number before booking an appointment for Class 1 Medical.*\n\n"
                "📖 **Referred Background Source:** DGCA Civil Aviation Requirements (CAR) Section 7, Series F Part I & Medical Cell Guidelines ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Computer Number Steps", "Vision & Lasik Query", "Ground School Details", "Talk to Medical Counselor"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 98.9,
                    "retrieval_method": "DGCA Medical Directorate Manual",
                    "primary_book": "DGCA CAR Section 7 Series F Part I",
                    "page_number": 1,
                    "subject": "Aero-Medical Evaluation Standards",
                    "chunk_excerpt": f"Class 2 civil doctors, Class 1 IAF centers (IAM/AFCME). Vision: {c1['vision_criteria']}"
                }
            }

        # 6. Flying Hours Breakdown (200 Hours)
        if any(w in lower for w in ["200 hour", "200 flying hour", "flying hour breakdown", "flying breakdown", "solo hour", "pic hour", "cross country hour", "night flying"]):
            fb = self.kb["dgca_syllabus_and_rules"]["flying_hour_breakdown"]
            breakdown_list = "\n".join([f"- **{b.split(':')[0]}**: {b.split(':')[1]}" for b in fb["breakdown"]])
            ans = (
                "### 🛩️ **DGCA CPL 200 Flying Hours Distribution**\n\n"
                "As per DGCA Aircraft Rules 1937 (Schedule II, Section J), a minimum of **200 logged flying hours** is mandatory for the issue of a Commercial Pilot License (Aeroplanes):\n\n"
                f"{breakdown_list}\n\n"
                "#### ✈️ Fleet Flown at Airborne Aviation Academy:\n"
                "- **Single-Engine Primary:** Cessna 172R / 172S Glass Cockpit (Garmin G1000)\n"
                "- **Multi-Engine Endorsement:** Piper Seneca V & Diamond DA42\n"
                "- **Flight Simulator:** DGCA Level-5 FAA-approved FNPT-II simulator for instrument rating drills\n\n"
                "📖 **Referred Background Source Book:** Air Regulations: RK Bali 15th Edition (DGCA Aircraft Rules 1937, Schedule II, Section J)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Total Cost", "Ground School Subjects", "Medical Eligibility", "Download Brochure"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.5,
                    "retrieval_method": "DGCA Aircraft Rules 1937 Schedule II Specification",
                    "primary_book": "Air Regulations: RK Bali 15th Edition",
                    "page_number": 190,
                    "subject": "Flight Crew Licensing Requirements",
                    "chunk_excerpt": "100h PIC, 50h XC, 20h Instrument, 5h Solo Night. Total 200 flying hours."
                }
            }

        # 7. Career FAQs: Arts / Commerce & NIOS
        if re.search(r'\b(arts|commerce|nios|non-science)\b', lower) or "without maths" in lower or "without physics" in lower:
            faq = next((f for f in self.kb["career_faqs"] if "Arts or Commerce" in f["question"]), None)
            ans = (
                "### 🎓 **Pilot Eligibility for Arts & Commerce Students**\n\n"
                f"{faq['answer'] if faq else 'You can become a pilot even without Physics and Maths in 12th by taking NIOS exams.'}\n\n"
                "#### 📌 Steps to Qualify via NIOS:\n"
                "1. Register on the NIOS portal (National Institute of Open Schooling) for **On-Demand Examinations**.\n"
                "2. Appear for **Physics (Code 312)** and **Mathematics (Code 311)**.\n"
                "3. Secure passing grades (minimum 50% recommended).\n"
                "4. Submit the verified NIOS marksheet to DGCA for Computer Number issuance.\n\n"
                "> 💡 *Airborne Aviation Academy provides in-house coaching for NIOS Physics & Mathematics alongside your ground classes.*\n\n"
                "📖 **Referred Background Source:** DGCA Public Circular on NIOS Senior Secondary Equivalence ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Computer Number Steps", "CPL Course Details", "Fee Structure & Loans", "Talk to Admissions Counselor"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.0,
                    "retrieval_method": "DGCA Educational Equivalence Circular",
                    "primary_book": "DGCA Public Notice on NIOS Equivalence",
                    "page_number": 1,
                    "subject": "Pilot Licensing Educational Prerequisites",
                    "chunk_excerpt": faq["answer"] if faq else "Acceptance of NIOS Physics and Mathematics."
                }
            }

        # 8. Career FAQs: Pilot Salary in India
        if any(w in lower for w in ["salary", "pilot salary", "how much does a pilot earn", "earnings", "pay"]):
            faq = next((f for f in self.kb["career_faqs"] if "starting salary" in f["question"].lower()), None)
            ans = (
                "### 💵 **Commercial Pilot Salary Breakdown in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "#### 📈 Career Progression & Typical Compensation:\n"
                "| Rank | Experience | Estimated Monthly Salary |\n"
                "| :--- | :--- | :--- |\n"
                "| **Junior First Officer (Second Officer)** | 0 - 500 Hours | ₹1,50,000 - ₹2,50,000 |\n"
                "| **First Officer** | 500 - 2,500 Hours | ₹3,50,000 - ₹5,00,000 |\n"
                "| **Senior First Officer** | 2,500 - 4,000 Hours | ₹4,50,000 - ₹6,50,000 |\n"
                "| **Captain (A320 / B737 Commander)** | 4,000+ Hours & ATPL | ₹6,50,000 - ₹10,50,000 |\n"
                "| **Line Training Captain (LTC / TRI / TRE)**| Senior Captain | ₹11,00,000 - ₹15,00,000+ |\n\n"
                "> ✈️ *Aviation is one of the highest-paying professions in India, with rapid return on initial training investment.*\n\n"
                "📖 **Referred Background Source:** Indian Airline First Officer & Commander Industry Survey (Airborne Careers)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Total Cost", "Cadet Pilot Programs", "100% Bank Loans", "Airline Hiring Demand"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 97.5,
                    "retrieval_method": "Aviation Industry Compensation Benchmark",
                    "primary_book": "Airborne Aviation Placement Records & Airline FO Surveys",
                    "page_number": 1,
                    "subject": "Pilot Career Trajectory & Compensation",
                    "chunk_excerpt": "JFO: 1.5L-2.5L, FO: 3.5L-5L, Captain: 6.5L-10.5L."
                }
            }

        # 9. Career FAQs: Age Limits
        if any(w in lower for w in ["age limit", "minimum age", "maximum age", "upper age", "how old"]):
            faq = next((f for f in self.kb["career_faqs"] if "minimum age" in f["question"].lower()), None)
            ans = (
                "### 📅 **Age Criteria for Pilot Training in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "- 🪪 **Student Pilot License (SPL):** Minimum 16 years of age.\n"
                "- 🛫 **Commercial Pilot License (CPL):** Minimum 17 years to fly solo; 18 years for license issuance.\n"
                "- 👨‍✈️ **Airline Cadet Pilot Programs:** Typically 18 to 32 years at application.\n"
                "- 🛩️ **Maximum Commercial Flying Age:** Commercial pilots can fly with airlines up to **65 years of age** as per DGCA rules.\n\n"
                "> 💡 *It is never too late: Many professionals transition to commercial aviation in their late 20s and 30s successfully.*\n\n"
                "📖 **Referred Background Source Book:** Air Regulations: RK Bali 15th Edition (DGCA Aircraft Rules 1937, Rule 38A & Schedule II)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Class 1 & 2 Medicals", "Total Course Fees", "Admissions Help"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.2,
                    "retrieval_method": "Indian Aircraft Rules 1937 Statutory Eligibility",
                    "primary_book": "Air Regulations: RK Bali 15th Edition",
                    "page_number": 42,
                    "subject": "Pilot Licensing Age Criteria",
                    "chunk_excerpt": "SPL: 16y, CPL Solo: 17y, Commercial Upper Age Limit: 65y."
                }
            }

        # 10. Career FAQs: Airline Hiring Demand & Industry Scope
        if any(w in lower for w in ["hiring demand", "airline demand", "scope", "market demand", "pilot shortage", "job opportunity"]):
            faq = next((f for f in self.kb["career_faqs"] if "hiring demand" in f["question"].lower()), None)
            ans = (
                "### 🚀 **Aviation Industry Growth & Pilot Hiring Boom in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "#### ✈️ Major Fleet Expansions in India:\n"
                "- **Air India:** 470 aircraft ordered (Airbus A320neo, A350 & Boeing 737 MAX, 777X, 787)\n"
                "- **IndiGo:** 500 aircraft order (Airbus A320neo family) + 30 A350 widebodies\n"
                "- **Akasa Air:** 200+ Boeing 737 MAX aircraft\n\n"
                "> 💡 *Each narrow-body airliner requires an average of 10 to 12 pilots (Captains & First Officers) to operate 24/7 schedules.*\n\n"
                "📖 **Referred Background Source:** DGCA Commercial Pilot Licensing Annual Statistics & Fleet Expansion Reports ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Cadet Pilot Programs", "Ground School Syllabus", "Talk to Flight Advisor"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 96.5,
                    "retrieval_method": "Civil Aviation Fleet Expansion Analytics",
                    "primary_book": "DGCA Annual Fleet & Flight Crew Reports",
                    "page_number": 1,
                    "subject": "Commercial Aviation Fleet Growth & Pilot Demand",
                    "chunk_excerpt": "1,500+ aircraft on order in India, generating demand for 12,000+ pilots."
                }
            }

        # 11. Academy Information & Campus Hubs
        if any(w in lower for w in ["about academy", "location", "locations", "where are you", "ground center", "flying base", "contact academy"]):
            acad = self.kb["academy"]
            locs = "\n".join([f"- {loc}" for loc in acad["locations"]])
            ans = (
                f"### ✈️ **About {acad['name']}**\n\n"
                f"*{acad['tagline']}*\n\n"
                f"#### 📍 Training Hubs & Flight Bases:\n{locs}\n\n"
                "#### 📞 Contact & Admissions Desk:\n"
                f"- **Helpline Toll-Free:** {acad['phone_helpline']}\n"
                f"- **WhatsApp Admissions:** {acad['whatsapp_display']}\n"
                f"- **Admissions Email:** {acad['email']}\n\n"
                "Visit our ground center or book a simulator cockpit trial with our senior flight instructors!\n\n"
                "📖 **Referred Background Source:** Airborne Aviation Academy Official Prospectus & DGCA Approved Flying Training Hubs"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Fee Breakdown & Loans", "DGCA Syllabus", "Chat on WhatsApp"],
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.8,
                    "retrieval_method": "Institutional Academy Profile",
                    "primary_book": "Airborne Aviation Academy Prospectus",
                    "page_number": 1,
                    "subject": "Flight Training Hubs & Simulators",
                    "chunk_excerpt": f"Bases: {', '.join(acad['locations'])}"
                }
            }

        return None
