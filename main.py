import sys
import os
import logging
import traceback

# 프로젝트 루트 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정 (파일과 콘솔 모두 출력)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

try:
    import wx
except ImportError:
    logger.critical("wxPython import failed!")
    sys.exit(1)

from app.app import AppContext
from app.ui.mainwindow import MainWindow

def main():
    """
    AnswerSelector_v2 진입점 (wxPython 버전).
    """
    try:
        # 1. wx.App 인스턴스 생성 (GUI 팝업을 위해 가장 먼저 생성)
        app = wx.App(False)
        
        # 2. 애플리케이션 컨텍스트 초기화
        logger.info("Initializing context...")
        
        # DataManager import for exception catching
        from app.managers.datamanager import MissingRequiredDataError
        
        try:
            context = AppContext()
            # 초기화 중 에러가 발생했더라도 init_error에 저장되고 객체는 생성됨
        except Exception as e:
            # AppContext 생성 자체 실패 시
            wx.MessageBox(f"앱 초기화 중 오류가 발생했습니다. 앱을 종료합니다.\n\n[종료사유]\n{e}", "앱 초기화 실패", wx.OK | wx.ICON_ERROR)
            logger.error(traceback.format_exc())
            sys.exit(1)

        # 3. 메인 윈도우 생성 및 표시
        logger.info("Creating main window...")
        frame = MainWindow(None, "AnswerSelector(민원답변검색기)", context)
        frame.Show()

        # 4. 시작 검증 로직 지연 실행 (윈도우가 뜬 후에 실행됨)
        def show_startup_checks():
            # 4-1. 필수 데이터 누락 체크
            if context.init_error:
                err = context.init_error
                if isinstance(err, MissingRequiredDataError):
                     msg = f"필수 데이터 파일이 없습니다. 앱을 종료합니다.\n\n[누락된 파일]\n{', '.join(err.missing)}"
                     wx.MessageBox(msg, "필수 데이터 누락", wx.OK | wx.ICON_ERROR)
                else:
                     msg = f"앱 초기화 중 오류가 발생했습니다. 앱을 종료합니다.\n\n[종료사유]\n{err}"
                     wx.MessageBox(msg, "앱 초기화 실패", wx.OK | wx.ICON_ERROR)
                
                logger.error(f"Startup check failed: {err}")
                frame.force_exit = True # 종료 확인창 스킵
                frame.Close() # 메인 윈도우 닫기
                sys.exit(1)

            # 4-2. 모델 유무에 따른 환영 메시지
            if context.has_model:
                wx.MessageBox(
                    "민원답변검색기 사용을 환영합니다.\n(문맥검색에 필요한 언어모델이 설치되어 있습니다)", 
                    "민원답변검색기", 
                    wx.OK | wx.ICON_INFORMATION
                )
            else:
                wx.MessageBox(
                    "민원답변검색기 사용을 환영합니다.\n(문맥검색에 필요한 언어모델이 없어 관련 기능이 제한됩니다)", 
                    "민원답변검색기", 
                    wx.OK | wx.ICON_INFORMATION
                )

        wx.CallAfter(show_startup_checks)

        # 5. 이벤트 루프 시작
        logger.info("Starting main loop...")
        app.MainLoop()
        
    except SystemExit:
        pass
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        logger.error(traceback.format_exc())
        
        # 앱 인스턴스가 있으면 메시지박스 시도
        if 'app' in locals() and app:
             wx.MessageBox(f"앱 동작 중 치명적인 오류가 발생하였습니다. 앱을 종료합니다.\n\n[종료사유]\n{e}", "오류 발생", wx.OK | wx.ICON_ERROR)
        
        sys.exit(1)

if __name__ == "__main__":
    main()
