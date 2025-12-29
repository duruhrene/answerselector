import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import onnxruntime as ort
from tokenizers import Tokenizer

class EmbedManager:
    """
    Manages ONNX-based embedding models for semantic retrieval.
    Handles tokenization, inference, pooling, and L2 normalization.
    """

    def __init__(self, model_dir: Optional[Any] = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else self._default_model_dir()
        
        self.tokenizer: Optional[Tokenizer] = None
        self.session: Optional[ort.InferenceSession] = None
        
        # Model Configuration (Loaded from model/model_info.json)
        self.model_config: Dict[str, Any] = {}
        
        # Default initialization (will be overwritten by json)
        self.hidden_size = 0
        self.max_length = 0
        self.output_name = ""
        self.use_pooling = False
        self.model_name = "Unknown"
        self.license = "Unknown"
        
        # 앱 시작 시 모델 유효성 검사 결과 (True인 경우에만 로드 시도 가능)
        self.is_valid_at_startup: bool = False
        
        self.top_k = 20  # App-level: Number of results to return (Keep as requested)

    def _default_model_dir(self) -> Path:
        """Resolve the default ONNX model directory."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / "model"

    def _load_config(self) -> bool:
        """Load model configuration from model_info with strict validation."""
        config_path = self.model_dir / "model_info"
        if not config_path.exists():
            print(f"Error: Model config file not found at {config_path}")
            return False
            
        try:
            import json
            with config_path.open("r", encoding="utf-8") as f:
                self.model_config = json.load(f)
            
            # 필수 키 목록
            required_keys = ["model_name", "license", "hidden_size", "max_length", "output_name", "use_pooling"]
            missing_keys = [key for key in required_keys if key not in self.model_config]
            
            if missing_keys:
                print(f"Error: Missing keys in model_info: {missing_keys}")
                return False
                
            self.hidden_size = self.model_config.get("hidden_size")
            self.max_length = self.model_config.get("max_length")
            self.output_name = self.model_config.get("output_name")
            self.use_pooling = self.model_config.get("use_pooling")
            self.model_name = self.model_config.get("model_name")
            self.license = self.model_config.get("license")
            
            return True
        except Exception as e:
            print(f"Error loading model config: {e}")
            return False

    def check_files(self) -> bool:
        """
        Check if all required model files exist AND config is valid.
        Required: model.onnx, tokenizer.json, model_info (valid JSON with keys)
        """
        files = ["model.onnx", "tokenizer.json", "model_info"]
        missing = []
        
        for f_name in files:
            f_path = self.model_dir / f_name
            if not f_path.exists():
                missing.append(f_name)
        
        if missing:
            print(f"Missing model files: {missing}")
            # 상세 복구 방법은 model/about_model_file.txt 파일을 참고하세요.
            self.is_valid_at_startup = False
            return False
            
        # 파일이 다 있다면 Config 내용 검증
        if not self._load_config():
            print("Invalid model_info file.")
            # 상세 복구 방법은 model/about_model_file.txt 파일을 참고하세요.
            self.is_valid_at_startup = False
            return False

        self.is_valid_at_startup = True
        return True

    def load_model(self) -> bool:
        """Initialize the ONNX session and tokenizer."""
        import wx
        error_msg = "언어모델 파일이 없거나 문제가 있어 로드할 수 없습니다.\n파일을 model 폴더에 넣은 후 앱을 다시 실행하세요."

        # 0. Check Startup Status first (Lock-out logic)
        # 앱 시작 시점에 이미 실패했다면, 지금 파일이 있어도 로드하지 않음 (재실행 강제)
        if not self.is_valid_at_startup:
            wx.MessageBox(error_msg, "언어모델 오류", wx.OK | wx.ICON_ERROR)
            return False

        # 1. Runtime Check (파일이 실행 중에 삭제되었을 수도 있으므로 안전장치)
        if not self.check_files():
            wx.MessageBox(error_msg, "언어모델 오류", wx.OK | wx.ICON_ERROR)
            return False

        # Config is already loaded by check_files() if it returned True

        model_path = self.model_dir / "model.onnx"
        tok_path = self.model_dir / "tokenizer.json"

        try:
            import wx # Ensure wx is available for error dialogs in this scope if needed
            
            # Load Tokenizer
            self.tokenizer = Tokenizer.from_file(str(tok_path))
            self.tokenizer.enable_truncation(max_length=self.max_length)
            self.tokenizer.enable_padding(length=self.max_length)

            # Load ONNX Session (CPU)
            providers = ['CPUExecutionProvider']
            self.session = ort.InferenceSession(str(model_path), providers=providers)
            
            return True
        except Exception as e:
            print(f"Error loading ONNX model: {e}")
            import wx
            wx.MessageBox(f"언어모델 로드 중 오류가 발생했습니다.\n(Error: {e})", "언어모델 오류", wx.OK | wx.ICON_ERROR)
            return False

    def unload_model(self) -> None:
        """Clear the ONNX session and tokenizer from memory."""
        self.tokenizer = None
        self.session = None

    def _mean_pooling(self, last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        """
        Perform Mean Pooling on the last hidden state, respecting the attention mask.
        """
        # Expand attention mask to match hidden state shape
        mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(float)
        
        # Multiply to zero out padding tokens and sum
        sum_embeddings = np.sum(last_hidden_state * mask_expanded, axis=1)
        
        # Count non-padded tokens and divide for mean
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
        
        return sum_embeddings / sum_mask

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate L2-normalized embedding for text using Numpy."""
        if not text:
            return None

        if self.session is None or self.tokenizer is None:
            if not self.load_model():
                return None

        try:
            # Tokenize
            encoded = self.tokenizer.encode(text)
            input_ids = np.array([encoded.ids], dtype=np.int64)
            attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

            # Inference
            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }
            outputs = self.session.run([self.output_name], inputs)
            raw_output = outputs[0]

            # Process Output (Pooling vs Direct)
            if self.use_pooling:
                # Mean Pooling (requires 3D output: [batch, seq, hidden])
                sentence_embedding = self._mean_pooling(raw_output, attention_mask)[0]
            else:
                # Direct Use (requires 2D output: [batch, hidden])
                sentence_embedding = raw_output[0]

            # L2 Normalization
            norm = np.linalg.norm(sentence_embedding)
            if norm > 0:
                sentence_embedding = sentence_embedding / norm
                
            return sentence_embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return None

    def search_similarity(self, query: str, documents: List[Dict[str, Any]], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Rank documents based on cosine similarity."""
        if top_k is None:
            top_k = self.top_k

        if not query or not documents:
            return []

        query_emb = self.get_embedding(query)
        if query_emb is None:
            print("Search error: Could not generate query embedding.")
            return []

        results = []
        for doc in documents:
            doc_emb_raw = doc.get("embedding")
            if not doc_emb_raw or len(doc_emb_raw) == 0:
                continue
                
            doc_emb = np.array(doc_emb_raw, dtype=np.float32)
            
            # Robust Cosine Similarity: (A . B) / (|A| * |B|)
            # Handles cases where vectors might not be pre-normalized.
            norm_q = np.linalg.norm(query_emb)
            norm_d = np.linalg.norm(doc_emb)
            
            if norm_q > 0 and norm_d > 0:
                similarity = float(np.dot(query_emb, doc_emb) / (norm_q * norm_d))
            else:
                similarity = 0.0

            result = doc.copy()
            result["score"] = similarity
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
