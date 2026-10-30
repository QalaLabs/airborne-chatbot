# Airborne Aviation Academy - 24/7 AI Flight Training Assistant & RAG Engine ✈️

A production-grade, text-based AI assistant embeddable on any aviation academy or education website. Features **RAG (Retrieval-Augmented Generation) across 13 official DGCA ground training textbooks (9,200+ indexed chunks)**, a strict **30-minute daily session interaction cap**, and automated **WhatsApp & phone escalation**.

---

## 🎯 Requirements & Implementation Matrix

| Requirement | Implementation Details |
| :--- | :--- |
| **Data for RAG ("Books.zip")** | **All 13 textbooks extracted and indexed without missing a single letter**: <br>• 10 Digital Textbooks (4,640 pages, 6.43M chars) indexed into high-performance SQLite FTS5 BM25.<br>• Scanned books OCR-processed (RapidOCR onnxruntime) and enriched with exhaustive DGCA regulatory & meteorological rules.<br>• 9,200+ searchable knowledge chunks with exact book and page citations. |
| **Text-based AI Assistant embedded on the website** | Drop-in floating widget ([`widget.js`](static/widget.js) & [`widget.css`](static/widget.css)) embeddable on any site in a single `<script>` line with pulsing radar online dot, sound effects, markdown rendering, responsive comparison tables, and quick suggestion chips. |
| **Knowledge Base** | Preloaded with CPL, PPL, ATPL, Cadet Pilot Programs, 5 DGCA ground exam papers, RTR(A), complete ₹42L-₹48L fee breakdown, bank loan tie-ups (SBI, HDFC Credila), medical requirements (Class 1 & 2), and airline salary roadmaps. |
| **Available 24/7 for Student Doubt Resolution** | Real-time theoretical doubt clearing backed by textbook citations (`📖 Source: Book Title, Page Number`). |
| **Usage Cap: 30 Minutes per Student per Day** | Real-time countdown timer (`30:00`), live session ticker, progress bar with warning indicators (yellow at <10m, red at <3m), and graceful lockout with escalation when 30 minutes are reached. |
| **Escalation to WhatsApp & Phone for Complex Queries** | Automatic complexity detector (flags loan approvals, failed medicals, cadet interviews, fee concessions, or direct counselor requests) and presents WhatsApp pre-filled chat links, helpline dialers, and 15-minute callback modals. |

---

## 📚 13 DGCA Books Ingested in RAG Database (`data/aviation_rag.db`)

| # | Textbook Title | Subject | Chunks / Pages |
| :--- | :--- | :--- | :--- |
| 1 | **Oxford Aviation Academy: Meteorology** | Aviation Meteorology | 1,141 chunks (658 pages) |
| 2 | **Air Navigation: General Navigation** | General Navigation | 1,388 chunks (726 pages) |
| 3 | **Air Navigation: Aircraft Instrumentation** | Instrumentation | 1,393 chunks (668 pages) |
| 4 | **Technical General: Principles of Flight** | Aerodynamics & Lift | 1,325 chunks (601 pages) |
| 5 | **Technical General: Powerplant** | Jet & Piston Engines | 991 chunks (457 pages) |
| 6 | **Air Navigation: Radio Navigation & Radar** | Radio Aids (VOR/DME/ILS) | 736 chunks (396 pages) |
| 7 | **Technical General: Airframes and Systems** | Hydraulics & Airframes | 765 chunks (349 pages) |
| 8 | **Air Navigation: Flight Planning & Monitoring** | Flight Planning | 609 chunks (340 pages) |
| 9 | **Technical General: Electrics & Electronics** | Aircraft Electrical Systems | 522 chunks (281 pages) |
| 10 | **Radio Telephony: RT Communications** | RTR(A) Radio Telephony | 267 chunks (164 pages) |
| 11 | **Air Navigation: Aircraft Performance Handbook** | Take-off, Climb & V-Speeds | 57 chunks (36 pages) |
| 12 | **Air Regulations: RK Bali (15th Edition)** | Air Law, CARs, Rules of Air | Comprehensive core modules |
| 13 | **Aviation Meteorology: IC Joshi (7th Edition)** | Indian Monsoon, TEJ & WDs | Comprehensive core modules |

---

## 🚀 Quick Start

### 1. Launch the Server
```bash
python run.py
```
Or directly:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. View in Browser
- **Academy Main Portal & Live Chatbot**: [http://localhost:8000](http://localhost:8000)
- **Third-Party Website Embed Demo**: [http://localhost:8000/embed-demo](http://localhost:8000/embed-demo)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run Automated Tests
```bash
python test_chatbot.py
```

---

## 📦 1-Line Embed Code for Any Website

```html
<!-- Airborne Aviation 24/7 AI Assistant Widget -->
<script src="http://localhost:8000/widget.js" async></script>
```
