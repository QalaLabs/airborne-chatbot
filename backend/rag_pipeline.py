import os
import re
import sqlite3
import time
import pymupdf
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("data/aviation_rag.db")
BOOKS_DIR = Path("data/Books")

# Book definitions mapping filenames to Subject and Display Title
BOOK_METADATA = {
    "Met Oxford Meteorology.pdf": {
        "title": "Oxford Aviation Academy: Meteorology",
        "subject": "Aviation Meteorology",
        "is_digital": True
    },
    "Nav Books - Flight Planning and Monitoring.pdf": {
        "title": "Air Navigation: Flight Planning & Monitoring",
        "subject": "Flight Planning",
        "is_digital": True
    },
    "Nav Books - General-Navigation.pdf": {
        "title": "Air Navigation: General Navigation",
        "subject": "General Navigation",
        "is_digital": True
    },
    "Nav Books - Instrumentation.pdf": {
        "title": "Air Navigation: Aircraft Instrumentation",
        "subject": "Instrumentation",
        "is_digital": True
    },
    "Nav Books - Radio Navigation.pdf": {
        "title": "Air Navigation: Radio Navigation & Radar",
        "subject": "Radio Navigation",
        "is_digital": True
    },
    "RT - RT Communications.pdf": {
        "title": "Radio Telephony: RTR(A) Communications & Phraseology",
        "subject": "Radio Telephony",
        "is_digital": True
    },
    "Tech Book 1 - Principles of Flight.pdf": {
        "title": "Technical General: Principles of Flight & Aerodynamics",
        "subject": "Principles of Flight",
        "is_digital": True
    },
    "Tech Book 2 - Airframes and Systems.pdf": {
        "title": "Technical General: Airframes, Hydraulics & Systems",
        "subject": "Airframes and Systems",
        "is_digital": True
    },
    "Tech Book 3 - Electrics and Electronics.pdf": {
        "title": "Technical General: Aircraft Electrics & Electronics",
        "subject": "Aircraft Electrics",
        "is_digital": True
    },
    "Tech Book 4 - Powerplant.pdf": {
        "title": "Technical General: Powerplant & Jet Engines",
        "subject": "Powerplant",
        "is_digital": True
    },
    "Nav Books - Performance Handbook.pdf": {
        "title": "Air Navigation: Aircraft Performance Handbook",
        "subject": "Aircraft Performance",
        "is_digital": False
    },
    "Met IC_Joshi_7 Edition.pdf": {
        "title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "is_digital": False
    },
    "Reg LATEST RK BALI REGULATION (Fifteenth Edition).pdf": {
        "title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "is_digital": False
    }
}

class AviationRAGPipeline:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), timeout=30.0)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init_db(self):
        with self._get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    filename TEXT UNIQUE,
                    title TEXT,
                    subject TEXT,
                    total_pages INTEGER,
                    is_digital INTEGER,
                    indexed_pages INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                );
            """)

            con.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT,
                    book_title TEXT,
                    subject TEXT,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    text TEXT,
                    char_count INTEGER,
                    FOREIGN KEY(book_id) REFERENCES books(id)
                );
            """)

            # FTS5 full-text search table with porter stemmer
            con.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    book_title,
                    subject,
                    text,
                    content='chunks',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
            """)

            # Triggers to keep FTS index synchronized with chunks table
            con.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, book_title, subject, text)
                    VALUES (new.id, new.book_title, new.subject, new.text);
                END;
            """)
            con.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, book_title, subject, text)
                    VALUES ('delete', old.id, old.book_title, old.subject, old.text);
                END;
            """)

    def chunk_text(self, text: str, target_size: int = 1000, overlap: int = 150) -> List[str]:
        """
        Splits text into coherent chunks targeting ~1000 characters while preserving sentence/paragraph boundaries.
        """
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text).strip()
        if not text:
            return []

        # Split into paragraphs or sentences
        paragraphs = text.split("\n")
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            
            p_len = len(p)
            if current_len + p_len <= target_size:
                current_chunk.append(p)
                current_len += p_len + 1
            else:
                if current_chunk:
                    chunk_str = "\n".join(current_chunk)
                    chunks.append(chunk_str)
                    # Keep overlap from the end of previous chunk
                    overlap_text = chunk_str[-overlap:] if len(chunk_str) > overlap else ""
                    current_chunk = [overlap_text, p] if overlap_text else [p]
                    current_len = len(overlap_text) + p_len + 1
                else:
                    # Single very long paragraph: split by sentence
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    for s in sentences:
                        if current_len + len(s) <= target_size:
                            current_chunk.append(s)
                            current_len += len(s) + 1
                        else:
                            if current_chunk:
                                chunks.append(" ".join(current_chunk))
                            current_chunk = [s]
                            current_len = len(s)

        if current_chunk:
            chunks.append("\n".join(current_chunk).strip())

        return [c for c in chunks if len(c.strip()) > 30]

    def index_digital_book(self, filename: str) -> int:
        """
        Extracts and indexes all pages of a digital PDF book into SQLite FTS5.
        """
        meta = BOOK_METADATA.get(filename)
        if not meta:
            return 0

        filepath = BOOKS_DIR / filename
        if not filepath.exists():
            print(f"[RAG] Warning: File not found {filepath}")
            return 0

        book_id = Path(filename).stem.lower().replace(" ", "_")
        doc = pymupdf.open(str(filepath))
        total_pages = len(doc)

        with self._get_connection() as con:
            # Register book
            con.execute("""
                INSERT OR REPLACE INTO books (id, filename, title, subject, total_pages, is_digital, status)
                VALUES (?, ?, ?, ?, ?, 1, 'indexing');
            """, (book_id, filename, meta["title"], meta["subject"], total_pages))

            # Delete existing chunks for this book if re-indexing
            con.execute("DELETE FROM chunks WHERE book_id = ?;", (book_id,))

            total_chunks = 0
            batch = []

            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                if not text or len(text.strip()) < 20:
                    continue

                chunks = self.chunk_text(text)
                for idx, chunk in enumerate(chunks):
                    batch.append((
                        book_id,
                        meta["title"],
                        meta["subject"],
                        page_num + 1,
                        idx + 1,
                        chunk,
                        len(chunk)
                    ))

                if len(batch) >= 200:
                    con.executemany("""
                        INSERT INTO chunks (book_id, book_title, subject, page_number, chunk_index, text, char_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, batch)
                    total_chunks += len(batch)
                    batch = []

            if batch:
                con.executemany("""
                    INSERT INTO chunks (book_id, book_title, subject, page_number, chunk_index, text, char_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, batch)
                total_chunks += len(batch)

            con.execute("""
                UPDATE books SET indexed_pages = ?, status = 'indexed' WHERE id = ?;
            """, (total_pages, book_id))

        doc.close()
        return total_chunks

    def index_all_digital_books(self) -> Dict[str, Any]:
        """
        Indexes all digital PDF books in the collection.
        """
        stats = {}
        total_indexed_chunks = 0
        t0 = time.time()

        for filename, meta in BOOK_METADATA.items():
            if meta.get("is_digital", False):
                filepath = BOOKS_DIR / filename
                if filepath.exists():
                    print(f"[RAG] Indexing digital book: {filename} ({meta['title']})...", flush=True)
                    count = self.index_digital_book(filename)
                    stats[filename] = count
                    total_indexed_chunks += count
                    print(f" -> Indexed {count} chunks.", flush=True)

        elapsed = time.time() - t0
        return {
            "books_indexed": stats,
            "total_chunks": total_indexed_chunks,
            "elapsed_seconds": round(elapsed, 2)
        }

    def search(self, query: str, top_k: int = 5, subject_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes hybrid BM25 full-text search against the DGCA aviation textbooks.
        """
        # Clean query for FTS5 syntax
        cleaned_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', query).split() if len(w) > 2]
        if not cleaned_words:
            return []

        # Build FTS match expression with OR / NEAR
        match_query = " OR ".join([f'"{w}"*' for w in cleaned_words[:8]])

        sql = """
            SELECT 
                c.id,
                c.book_title,
                c.subject,
                c.page_number,
                c.text,
                bm25(chunks_fts) as rank_score
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.rowid
            WHERE chunks_fts MATCH ?
        """
        params = [match_query]

        if subject_filter:
            sql += " AND c.subject LIKE ?"
            params.append(f"%{subject_filter}%")

        sql += " ORDER BY rank_score ASC LIMIT ?;"
        params.append(top_k)

        results = []
        try:
            with self._get_connection() as con:
                rows = con.execute(sql, params).fetchall()
                for row in rows:
                    results.append({
                        "chunk_id": row[0],
                        "book_title": row[1],
                        "subject": row[2],
                        "page_number": row[3],
                        "text": row[4],
                        "score": round(abs(row[5]), 3)
                    })
        except Exception as e:
            print(f"[RAG] Search error: {e}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Returns total books, pages and chunk counts in RAG database"""
        with self._get_connection() as con:
            book_rows = con.execute("SELECT id, title, subject, total_pages, indexed_pages, status FROM books;").fetchall()
            chunk_count = con.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]

        return {
            "total_chunks": chunk_count,
            "books": [
                {
                    "id": r[0],
                    "title": r[1],
                    "subject": r[2],
                    "total_pages": r[3],
                    "indexed_pages": r[4],
                    "status": r[5]
                }
                for r in book_rows
            ]
        }

rag_pipeline = AviationRAGPipeline()
