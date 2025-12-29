import sys
import logging
from pathlib import Path
from typing import Optional

from app.managers.datamanager import DataManager
from app.managers.userdatamanager import UserDataManager
from app.managers.embedmanager import EmbedManager
from app.managers.selectionmanager import SelectionManager

class AppContext:
    """
    애플리케이션의 모든 매니저 객체를 소유하고 관리하는 컨텍스트 클래스.
    UI 위젯들은 이 객체를 통해 데이터에 접근합니다.
    """
    def __init__(self, base_dir: Optional[Path] = None):
        # 1. 경로 설정
        # 1. 경로 설정
        if base_dir is None:
            if getattr(sys, 'frozen', False):
                # PyInstaller 패키징 환경 (onedir)
                # 실행 파일이 있는 폴더를 기준으로 함
                base_dir = Path(sys.executable).parent
            else:
                # 개발 환경 (main.py가 있는 루트 경로)
                # app/app.py 기준 2단 위: app/ -> AnswerSelector_v2/
                base_dir = Path(__file__).resolve().parent.parent
        else:
            base_dir = Path(base_dir)
        
        self.base_dir = base_dir
        
        # 로그 설정
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("AnswerSelectorV2")

        # 2. 매니저 초기화
        self.logger.info("Initializing managers...")
        db_dir = self.base_dir / "database"
        
        # 시스템 데이터 매니저 (answersembed.db, agencies.db 등)
        self.data = DataManager(db_dir)
        
        # 사용자 데이터 매니저 (usertemplates.db, usermemos.db)
        self.user = UserDataManager(db_dir)
        
        # 답변 선택 상태 매니저 (휘발성 S1~S3)
        self.selection = SelectionManager()
        
        # 임베딩 엔진 매니저 (ONNX 모델 로드/언로드)
        model_dir = self.base_dir / "model"
        self.embed = EmbedManager(model_dir)

        # 3. 데이터 로드 (중요: UI 실행 전에 데이터가 준비되어야 함)
        self.logger.info("Loading system data...")
        self.init_error = None
        try:
            self.data.load_all() 
        except Exception as e:
            # 필수 데이터 누락 등의 치명적 에러를 저장해두고, UI가 뜬 뒤에 처리하도록 함
            self.logger.error(f"Data loading failed: {e}")
            self.init_error = e

        # 4. 모델 파일 존재 여부 확인 (초기화 트리거)
        self.embed.check_files()

        # 5. 앱 정보 (버전 및 저작권) 로드
        self.app_info = self._load_app_info()

        self.logger.info("All managers initialized.")

    @property
    def has_model(self) -> bool:
        """
        모델 사용 가능 여부를 반환합니다.
        EmbedManager의 실시간 상태(is_valid_at_startup)를 반영합니다.
        """
        # embed 매니저가 없거나 초기화되지 않았으면 False
        if not hasattr(self, 'embed') or self.embed is None:
            return False
        return self.embed.is_valid_at_startup

    def _load_app_info(self) -> dict:
        """
        copyright_default.json 파일을 로드하여 앱 정보를 반환합니다.
        파일이 없거나 유효하지 않으면 기본값을 사용합니다.
        
        경로 규칙:
        - 개발 환경: app/copyright_default.json (app.py와 같은 폴더)
        - 배포 환경: _internal/copyright_default.json (exe 실행 위치의 _internal 폴더)
        """
        default_info = {
            "version": "v1.0.0 (2025-12-30)",
            "copyright": "Copyright (c) 2025-2026 Duruhrene. All rights reserved."
        }
        
        # 1. 개발/빌드 환경에 따라 파일 경로 결정
        if getattr(sys, 'frozen', False):
             # 빌드된(Frozen) 상태: _internal 폴더 내부 확인
             # base_dir은 sys.executable의 부모(dist/AnswerSelector)이므로 _internal을 명시해야 함
             json_path = self.base_dir / "_internal" / "copyright_internal"
        else:
             # 개발 환경: app 폴더 내부 확인
             json_path = self.base_dir / "app" / "copyright_internal"
            
        if json_path and json_path.exists():
            try:
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 필수 키가 다 있는지 확인
                    if "version" in data and "copyright" in data:
                        self.logger.info(f"Loaded app info from {json_path}")
                        return data
            except Exception:
                pass
        
        # 통합된 에러/기본값 처리
        self.logger.info("Invalid copyright_internal file. Using defaults.")
        
        # [복구 안내] copyright_internal 파일을 분실했을 경우
        # 아래 내용으로 빌드된 exe 폴더 내 _internal 폴더에 'copyright_internal' (확장자 없음) 파일을 생성하세요.
        # {
        #     "version": "v1.0.0 (2025-12-30)",
        #     "copyright": "Copyright (c) 2025-2026 (개발자 정보). All rights reserved."
        # }
        return default_info

    def close(self):
        """앱 종료 시 자원을 정리합니다."""
        self.logger.info("Closing application context...")
        # 필요한 경우 DB 연결 종료 등 추가
        pass

