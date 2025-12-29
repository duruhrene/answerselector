import wx
import logging

class AnswerBuilder(wx.Panel):
    """
    고정 패널: 서문/답변슬롯/결문을 조합하여 최종 텍스트를 생성하는 위젯 (wxPython Native).
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.logger = logging.getLogger("AnswerBuilder")
        self._is_manual_edited = False
        
        # UI 구성
        self._init_ui()
        
        # 데이터 시그널(Observer) 연결 - SelectionManager가 이제 순수 Python 객체임
        self.context.selection.add_observer(self._on_slot_changed)
        
        # 초기 초기화
        self._load_categories()
        self._assemble_fulltext()

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. 서문 및 결문 섹션 (StaticBoxSizer)
        config_box = wx.StaticBox(self, label="서문 및 결문")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        self.intro_combo = wx.Choice(config_box)
        self.intro_combo.Bind(wx.EVT_CHOICE, self.OnComboChanged)
        
        self.closing_combo = wx.Choice(config_box)
        self.closing_combo.Bind(wx.EVT_CHOICE, self.OnComboChanged)
        
        config_sizer.Add(self.intro_combo, 0, wx.EXPAND | wx.ALL, 2)
        config_sizer.Add(self.closing_combo, 0, wx.EXPAND | wx.ALL, 2)
        
        main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 2)

        # 2. 답변 슬롯 상태 (S1, S2, S3)
        slot_box = wx.StaticBox(self, label="슬롯 상태")
        slot_sizer = wx.StaticBoxSizer(slot_box, wx.HORIZONTAL)
        
        self.slot_labels = {}
        for slot in ["S1", "S2", "S3"]:
            lbl = wx.StaticText(slot_box, label=f"{slot}: (비었음)", style=wx.ALIGN_CENTER)
            self.slot_labels[slot] = lbl
            slot_sizer.Add(lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
            
        main_sizer.Add(slot_sizer, 0, wx.EXPAND | wx.ALL, 2)

        # 3. 템플릿 제목
        self.title_edit = wx.TextCtrl(self)
        self.title_edit.SetHint("템플릿 제목")
        main_sizer.Add(self.title_edit, 0, wx.EXPAND | wx.ALL, 2)

        # 4. 최종 조합창 (Fulltext)
        self.text_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.text_edit.Bind(wx.EVT_TEXT, self._on_text_edited)
        main_sizer.Add(self.text_edit, 1, wx.EXPAND | wx.ALL, 2)

        # 5. 작업 버튼
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_recall = wx.Button(self, label="다시 불러오기")
        self.btn_recall.Bind(wx.EVT_BUTTON, self._on_recall_template)
        
        self.btn_save = wx.Button(self, label="템플릿 저장")
        self.btn_save.Bind(wx.EVT_BUTTON, self._on_save_template)
        
        self.btn_clear = wx.Button(self, label="초기화")
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear)
        
        self.btn_copy = wx.Button(self, label="클립보드로")
        self.btn_copy.Bind(wx.EVT_BUTTON, self._on_copy)
        
        btn_sizer.Add(self.btn_recall, 1, wx.ALL, 2)
        btn_sizer.Add(self.btn_save, 1, wx.ALL, 2)
        btn_sizer.Add(self.btn_clear, 1, wx.ALL, 2)
        btn_sizer.Add(self.btn_copy, 1, wx.ALL, 2)
        
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 2)

        # 우측 고정 영역의 밸런스를 위해 전체 레이아웃에 우측/하단 여백 2px 추가
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(main_sizer, 1, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 4)
        self.SetSizer(outer_sizer)

    # --- 데이터 로딩 ---
    def _load_categories(self):
        # ClientData를 콤보박스에 함께 저장할 수 있음 (wx.ClientData 미사용 시, 별도 리스트 관리 필요하거나 Append(text, data) 사용)
        # wx.Choice.Append(item, clientData) 사용 가능
        
        # Intro
        self.intro_combo.Clear()
        self.intro_combo.Append("서문 선택", "") # clientData=""
        self.intro_combo.SetSelection(0)
        
        for cat in self.context.data.get_intro_cats():
            items = self.context.data.get_intros(cat)
            if items:
                # 보여질 텍스트는 카테고리명, 실제 데이터는 본문
                self.intro_combo.Append(cat, items[0]['text'])

        # Closing
        self.closing_combo.Clear()
        self.closing_combo.Append("결문 선택", "")
        self.closing_combo.SetSelection(0)
        
        for cat in self.context.data.get_closing_cats():
            items = self.context.data.get_closings(cat)
            if items:
                self.closing_combo.Append(cat, items[0]['text'])

    def OnComboChanged(self, event):
        self._assemble_fulltext()

    # --- 조립 로직 ---
    def _on_slot_changed(self, slot_name):
        """슬롯 데이터 변경 시 라벨 업데이트 및 자동 조립 (메인 스레드 안전 처리 권장)"""
        # wx.CallAfter를 사용하여 UI 스레드에서 실행 보장
        wx.CallAfter(self._update_slot_ui, slot_name)

    def _update_slot_ui(self, slot_name):
        # 1. UI 업데이트 및 조립 진행 (무조건 덮어쓰기)
        data = self.context.selection.get_slot(slot_name)
        lbl = self.slot_labels.get(slot_name)
        if not lbl:
            return
            
        if data:
            lbl.SetLabel(f"{slot_name}: {data.get('code', 'Unknown')}")
            font = lbl.GetFont()
            font.MakeBold()
            lbl.SetFont(font)
        else:
            lbl.SetLabel(f"{slot_name}: (비었음)")
            font = lbl.GetFont()
            font.MakeBold()
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            lbl.SetFont(font)
            
        lbl.Refresh()
        self._assemble_fulltext()

    def _on_text_edited(self, event):
        if self.text_edit.HasFocus():
            self._is_manual_edited = True
        event.Skip()

    def _assemble_fulltext(self):
        parts = []
        
        # 1. 서문
        sel_idx = self.intro_combo.GetSelection()
        if sel_idx != wx.NOT_FOUND:
            intro_text = self.intro_combo.GetClientData(sel_idx)
            if intro_text:
                parts.append(intro_text)
            
        # 2. 슬롯
        for slot in ["S1", "S2", "S3"]:
            data = self.context.selection.get_slot(slot)
            if data and data.get("text"):
                parts.append(data["text"])
                
        # 3. 결문
        sel_idx = self.closing_combo.GetSelection()
        if sel_idx != wx.NOT_FOUND:
            closing_text = self.closing_combo.GetClientData(sel_idx)
            if closing_text:
                parts.append(closing_text)
            
        processed_parts = [p.strip().replace('\\n', '\n') for p in parts if p.strip()]
        fulltext = "\n\n".join(processed_parts)
        
        self.text_edit.ChangeValue(fulltext) # ChangeValue는 이벤트를 발생시키지 않음 (setValue와 유사)
        self._is_manual_edited = False

    # --- 작업 버튼 ---
    def _on_recall_template(self, event):
        if self._is_manual_edited:
            ret = wx.MessageBox("기존에 저장된 슬롯의 내용으로 복원됩니다.", "다시 불러오기", wx.YES_NO | wx.ICON_QUESTION, self  # parent
            )
            if ret == wx.NO:
                return
        
        self._assemble_fulltext()

    def _on_save_template(self, event):
        title = self.title_edit.GetValue().strip()
        if not title:
            wx.MessageBox("저장할 템플릿의 제목을 입력하시기 바랍니다.", "제목 입력", wx.OK | wx.ICON_WARNING)
            return

        content = self.text_edit.GetValue().strip()
        if not content:
            wx.MessageBox("저장할 템플릿의 내용을 입력(선택)하시기 바랍니다.", "내용 입력", wx.OK | wx.ICON_WARNING)
            return
            
        existing = self.context.user.get_template_by_title(title)
        if existing:
            wx.MessageBox(f"'{title}'은(는) 이미 존재하는 제목입니다. 다른 제목을 입력하세요.", "제목 중복", wx.OK | wx.ICON_WARNING)
            return
        
        # 저장 확인 단계 추가
        ret = wx.MessageBox("입력하신 내용으로 새로운 템플릿이 생성됩니다.", "생성 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO:
            return
            
        success = self.context.user.add_template(title, content)
        if not success:
            wx.MessageBox("템플릿 저장에 실패했습니다.", "저장 실패", wx.OK | wx.ICON_ERROR)

    def _on_copy(self, event):
        content = self.text_edit.GetValue().strip()
        if content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(content))
                wx.TheClipboard.Close()
                wx.MessageBox("현재 입력된 내용이 클립보드로 복사되었습니다.", "클립보드로 복사", wx.OK | wx.ICON_INFORMATION)

    def _on_clear(self, event):
        ret = wx.MessageBox(
            "서문/결문 및 슬롯(입력하신 내용 포함)이 초기화됩니다.", "초기화 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO:
            return

        self.intro_combo.SetSelection(0)
        self.closing_combo.SetSelection(0)
        self.context.selection.clear_all()
        self._is_manual_edited = False
