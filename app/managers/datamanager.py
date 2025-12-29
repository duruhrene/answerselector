import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

class MissingRequiredDataError(RuntimeError):
    """Raised when required database/json files are missing."""
    def __init__(self, missing: List[str]) -> None:
        super().__init__(f"Missing required data files: {', '.join(missing)}")
        self.missing = missing

class DataManager:
    """
    Data loading and indexing for AnswerSelector V2.
    
    Data Sources:
      1. answersembed.db (SQLite): Main content (cat1/cat2/cat3, embedding)
      2. agencies.db (SQLite): Agency info
      3. introclosing.db (SQLite): Intro/Closing texts
      4. conjunctions.json (JSON): Conjunction strings
    """

    def __init__(self, db_dir: Optional[Any] = None) -> None:
        self.db_dir = Path(db_dir) if db_dir is not None else self._default_db_dir()

        # Data Containers (List for records, Dict for lookup maps)
        self.answers: List[Dict[str, Any]] = []
        self.agencies: Dict[str, Dict[str, Any]] = {} 
        self.conjunctions: List[str] = []
        self.intro_closing: List[Dict[str, Any]] = [] 

        # Indexes
        self.by_code: Dict[str, Dict[str, Any]] = {}
        self.by_id: Dict[int, Dict[str, Any]] = {}
        # index_tree: cat1 -> cat2 -> cat3 -> List[Record]
        self.index_tree: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
        # intro_index: type -> cat -> List[Record]
        self.intro_index: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "intro": {}, 
            "closing": {}
        }

    def load_all(self) -> None:
        """Load all data sources and build indexes."""
        self._ensure_required_files()
        
        self._load_answers()
        self._load_agencies()
        self._load_intro_closing()
        self._load_conjunctions()
        
        self._build_indexes()

    # ------------------------------------------------------------------ #
    # Internal: Path & Validation
    # ------------------------------------------------------------------ #
    def _default_db_dir(self) -> Path:
        """Resolve database directory."""
        # 기본적으로 app/managers/../../database (개발환경 기준)
        # 하지만 실제로는 AppContext에서 올바른 경로(base_dir/database)를 주입받아야 함.
        # 이 메서드는 주입받지 못한 비상 상황용 fallback.
        return Path(__file__).resolve().parent.parent.parent / "database"

    def _ensure_required_files(self) -> None:
        required = [
            "answersembed.db",
            "agencies.db",
            "introclosing.db",
            "conjunctions.json"
        ]
        missing = [fname for fname in required if not (self.db_dir / fname).exists()]
        if missing:
            raise MissingRequiredDataError(missing)

    # ------------------------------------------------------------------ #
    # Internal: Loaders
    # ------------------------------------------------------------------ #
    def _load_answers(self) -> None:
        db_path = self.db_dir / "answersembed.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, code, cat1, cat2, cat3, title, maintext, agency1, agency2, embedding FROM answerembed")
            rows = cursor.fetchall()
            
            self.answers = []
            for row in rows:
                record = dict(row)
                emb_str = record.get("embedding")
                if emb_str:
                    try:
                        record["embedding"] = json.loads(emb_str)
                    except json.JSONDecodeError:
                        record["embedding"] = []
                else:
                    record["embedding"] = []
                self.answers.append(record)

    def _load_agencies(self) -> None:
        db_path = self.db_dir / "agencies.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, name, website, tel, paid FROM agencies")
            rows = cursor.fetchall()
            
            self.agencies = {}
            for row in rows:
                r_dict = dict(row)
                name = r_dict.get("name")
                if name:
                    self.agencies[name] = r_dict

    def _load_intro_closing(self) -> None:
        db_path = self.db_dir / "introclosing.db"
        self.intro_closing = []
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, type, cat, text FROM introclosing")
            rows = cursor.fetchall()
            
            for row in rows:
                self.intro_closing.append(dict(row))

    def _load_conjunctions(self) -> None:
        json_path = self.db_dir / "conjunctions.json"
        with json_path.open("r", encoding="utf-8") as f:
            self.conjunctions = json.load(f)

    def _build_indexes(self) -> None:
        # 1. Answer Indexes
        self.by_code = {}
        self.by_id = {}
        self.index_tree = {}

        for rec in self.answers:
            code = rec.get("code")
            if code:
                self.by_code[code] = rec
            
            ans_id = rec.get("id")
            if ans_id is not None:
                self.by_id[ans_id] = rec
            
            c1 = rec.get("cat1") or "Unknown"
            c2 = rec.get("cat2") or "Unknown"
            c3 = rec.get("cat3") or "Unknown"

            if c1 not in self.index_tree:
                self.index_tree[c1] = {}
            if c2 not in self.index_tree[c1]:
                self.index_tree[c1][c2] = {}
            if c3 not in self.index_tree[c1][c2]:
                self.index_tree[c1][c2][c3] = []
            
            self.index_tree[c1][c2][c3].append(rec)

        # 2. Intro/Closing Index
        self.intro_index = {"intro": {}, "closing": {}}
        for item in self.intro_closing:
            t = item.get("type") 
            c = item.get("cat")
            
            # Legacy logic: hardcoded bucket filtering
            if t in self.intro_index:
                if c not in self.intro_index[t]:
                    self.intro_index[t][c] = []
                self.intro_index[t][c].append(item)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    
    # --- Answer Access ---
    def get_all_answers(self) -> List[Dict[str, Any]]:
        return self.answers

    def get_answer_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        return self.by_code.get(code)
    
    def get_answer_by_id(self, ans_id: int) -> Optional[Dict[str, Any]]:
        return self.by_id.get(ans_id)
    
    def search_answers(self, keyword: str) -> List[Dict[str, Any]]:
        """Search answers by keyword (matches title or content)."""
        if not keyword:
            return []
        
        results = []
        for rec in self.answers:
            title = rec.get("title") or ""
            text = rec.get("maintext") or ""
            
            if keyword in title or keyword in text:
                results.append(rec)
                
        return results
    
    # --- Category Hierarchy Access ---
    def get_cat1_list(self) -> List[str]:
        return list(self.index_tree.keys())

    def get_cat2_list(self, cat1: str) -> List[str]:
        if cat1 in self.index_tree:
            return list(self.index_tree[cat1].keys())
        
        return []

    def get_cat3_list(self, cat2: str, cat1: str) -> List[str]:
        if cat1 in self.index_tree:
            if cat2 in self.index_tree[cat1]:
                return list(self.index_tree[cat1][cat2].keys())
            return []
        
        return []
        
    def get_answers_in_cat3(self, cat2: str, cat3: str, cat1: str) -> List[Dict[str, Any]]:
        if cat1 in self.index_tree:
            try:
                return self.index_tree[cat1][cat2][cat3]
            except KeyError:
                return []

        return []

    # --- Agency Access ---
    def get_agency(self, name: str) -> Optional[Dict[str, Any]]:
        return self.agencies.get(name)

    # --- Conjunctions ---
    def get_conjunction_list(self) -> List[str]:
        return self.conjunctions

    # --- Intro/Closing Access (Reverted to specific methods) ---
    def get_intro_cats(self) -> List[str]:
        return list(self.intro_index["intro"].keys())

    def get_closing_cats(self) -> List[str]:
        return list(self.intro_index["closing"].keys())

    def get_intros(self, cat: str) -> List[Dict[str, Any]]:
        """Returns list of dicts: [{'id':..., 'text':...}, ...]"""
        return self.intro_index["intro"].get(cat, [])

    def get_closings(self, cat: str) -> List[Dict[str, Any]]:
        return self.intro_index["closing"].get(cat, [])
