import wx
import logging

class MainWindow(wx.Frame):
    """
    AnswerSelector의 메인 윈도우 (wxPython).
    좌측 탭(Notebook)과 우측 빌더(Panel)를 SplitterWindow로 분할하여 구성합니다.
    """
    def __init__(self, parent, title, context):
        super().__init__(parent, title=title, size=(1200, 900))
        self.context = context
        self.logger = logging.getLogger("MainWindow")
        self.force_exit = False # 강제 종료 플래그

        self.InitUI()
        self.Centre()
        
        # 앱 종료 이벤트 바인딩 (X 버튼, Alt+F4 등)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def InitUI(self):
        # 1. 메뉴바 설정
        self._init_menu_bar()

        # 2. 메인 패널 및 레이아웃 설정
        # wx.Frame 안에 위젯을 직접 넣기보다 wx.Panel을 하나 깔고 그 위에 구성하는 것이 관례(배경색 등 호환성)
        self.main_panel = wx.Panel(self)
        
        # 메인 레이아웃 (VBox)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 3. Splitter Window (좌: 탭, 우: 빌더)
        self.splitter = wx.SplitterWindow(self.main_panel, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSashChanging)
        self.splitter.SetMinimumPaneSize(300) # 패널 최소 크기

        # --- 좌측: 탭 패널 (Notebook) ---
        self.notebook = wx.Notebook(self.splitter)
        
        # TODO: 추후 각 모듈이 wxPython으로 포팅되면 import하여 교체
        from app.ui.catsearch import CatSearch
        self.cat_search_tab = CatSearch(self.notebook, self.context)
        
        from app.ui.textsearch import TextSearch
        self.text_search_tab = TextSearch(self.notebook, self.context)
        
        from app.ui.templateeditor import TemplateEditor
        self.template_editor_tab = TemplateEditor(self.notebook, self.context)

        self.notebook.AddPage(self.template_editor_tab, "템플릿 관리")
        self.notebook.AddPage(self.cat_search_tab, "카테고리 검색")
        self.notebook.AddPage(self.text_search_tab, "텍스트 검색")

        # --- 우측: 빌더 패널 (AnswerBuilder) ---
        from app.ui.answerbuilder import AnswerBuilder
        self.builder_panel = AnswerBuilder(self.splitter, self.context)

        # Splitter 나누기 (좌측 2 : 우측 1 비율)
        # 초기 사이즈가 결정된 후(CallAfter)에 정확한 비율로 Sash 위치를 조정해야 함
        self.splitter.SplitVertically(self.notebook, self.builder_panel)
        self.splitter.SetSashGravity(0.66)
        wx.CallAfter(self._set_initial_sash_pos)

        # Main Sizer에 Splitter 추가 (비율 1, 확장 가능)
        main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 2)

        self.main_panel.SetSizer(main_sizer)

    def _set_initial_sash_pos(self):
        """윈도우가 표시된 직후 정확한 2:1 비율로 Sash 위치 조정"""
        total_width = self.splitter.GetClientSize().GetWidth()
        self.splitter.SetSashPosition(int(total_width * 0.66))

    def OnSashChanging(self, event):
        """구분선 드래그를 방지하여 2:1 비율 고정"""
        event.Veto()

    def _init_menu_bar(self):
        menubar = wx.MenuBar()

        # 도움말 메뉴
        help_menu = wx.Menu()
        
        # 라이선스 서브메뉴
        license_submenu = wx.Menu()
        
        # 1. 외부 패키지(소프트웨어) 라이선스
        pkg_license_item = license_submenu.Append(wx.ID_ANY, "외부 패키지(소프트웨어) 라이선스", "외부 패키지(소프트웨어) 라이선스 정보")
        self.Bind(wx.EVT_MENU, self.OnPackageLicense, pkg_license_item)
        
        # 2. 언어모델 라이선스 (생성만)
        model_license_item = license_submenu.Append(wx.ID_ANY, "언어모델 라이선스", "언어모델 라이선스 정보")
        self.Bind(wx.EVT_MENU, self.OnModelLicense, model_license_item)
        
        # 서브메뉴를 도움말 메뉴에 추가
        help_menu.AppendSubMenu(license_submenu, "라이선스")
        
        help_menu.AppendSeparator()

        # 애플리케이션 정보
        about_item = help_menu.Append(wx.ID_ABOUT, "애플리케이션 정보(&A)", "애플리케이션 정보")
        self.Bind(wx.EVT_MENU, self.OnAbout, about_item)
        
        menubar.Append(help_menu, "도움말(&H)")

        self.SetMenuBar(menubar)

    def OnClose(self, event):
        """앱 종료 시 확인"""
        # 강제 종료 모드이거나 Veto 불가능한 경우(시스템 강제 종료)는 확인창 스킵
        if self.force_exit or not event.CanVeto():
            self.Destroy()
            return

        if wx.MessageBox("앱을 종료하시겠습니까? 저장하지 않은 내용은 손실됩니다.", 
                         "종료 확인", 
                         wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            event.Veto()
            return
        
        self.Destroy()

    def OnAbout(self, event):
        info = self.context.app_info
        version = info.get("version", "Unknown Version")
        copyright_text = info.get("copyright", "Unknown Copyright")
        
        wx.MessageBox(f"AnswerSelector(민원답변검색기)\n{version}\n{copyright_text}", 
                      "애플리케이션 정보", wx.OK | wx.ICON_INFORMATION)

    def OnPackageLicense(self, event):
        license_path = self.context.base_dir / "THIRDPARTY_LICENSE.txt"
        if license_path.exists():
            try:
                with open(license_path, 'r', encoding='utf-8') as f:
                    info_text = f.read()
            except Exception as e:
                info_text = f"라이선스 파일을 읽는 중 오류가 발생했습니다.\n{e}"
        else:
            info_text = "THIRDPARTY_LICENSE.txt 파일을 찾을 수 없습니다."

        # 별도의 다이얼로그 생성
        dlg = wx.Dialog(self, title="외부 패키지(소프트웨어) 라이선스", size=(750, 750))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 안내 문구 (읽기 전용, 멀티라인 텍스트 박스)
        tc = wx.TextCtrl(dlg, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        tc.SetValue(info_text)
        
        vbox.Add(tc, 1, wx.EXPAND | wx.ALL, 10)
        
        # 닫기 버튼
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(wx.Button(dlg, wx.ID_OK, label="닫기"))
        btn_sizer.Realize()
        
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        dlg.SetSizer(vbox)
        dlg.CentreOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def OnModelLicense(self, event):
        """언어모델 라이선스 정보 표시"""
        # 3. 모델 파일이 하나라도 없으면(has_model=False) 에러 메시지 표시
        if not self.context.has_model:
            wx.MessageBox("언어모델 파일이 없거나 문제가 있어 로드할 수 없습니다.\n파일을 model 폴더에 넣은 후 앱을 다시 실행하세요.", 
                          "언어모델 오류", wx.OK | wx.ICON_ERROR)
            return
            
        embed_mgr = self.context.embed
        
        # has_model이 True라면 이미 Config 로드가 완료된 상태임
        model_name = embed_mgr.model_name
        model_license = embed_mgr.license
        
        info_text = (
            f"Model: {model_name}\n"
            f"License: {model_license}"
        )
        
        # 별도의 다이얼로그 생성 (복사 가능하도록 TextCtrl 사용)
        dlg = wx.Dialog(self, title="언어모델 라이선스", size=(500, 200))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 안내 문구 (읽기 전용, 멀티라인 텍스트 박스)
        tc = wx.TextCtrl(dlg, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
        tc.SetValue(info_text)
        
        vbox.Add(tc, 1, wx.EXPAND | wx.ALL, 10)
        
        # 닫기 버튼
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(wx.Button(dlg, wx.ID_OK, label="닫기"))
        btn_sizer.Realize()
        
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        dlg.SetSizer(vbox)
        dlg.CentreOnParent()
        dlg.ShowModal()
        dlg.Destroy()
