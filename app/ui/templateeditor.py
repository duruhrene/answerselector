import wx
import logging

class TemplateEditor(wx.Panel):
    """저장된 템플릿 목록을 조회, 수정, 삭제하는 패널 (wxPython Native)."""
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.current_templates = []
        self.current_template = None
        self.InitUI()
        
        # Subscribe to data changes
        self.context.user.add_observer(self._on_data_changed)

    def _on_data_changed(self, event_type):
        """Called when templates are added/updated/deleted."""
        # UI 스레드에서 UI 갱신 보장
        wx.CallAfter(self._refresh_list)

    def _refresh_list(self):
        # 현재 모드(전체/검색)에 따라 리스트 갱신
        if self.all_radio.GetValue():
            self._load_all_templates()
        elif self.query_radio.GetValue():
            # 검색 모드라면 검색어 유지하며 재검색
            self._on_search_clicked(None)

    def InitUI(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- 1. Top Bar: Modes (Row 1) ---
        top_row1 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.all_radio = wx.RadioButton(self, label="전체보기", style=wx.RB_GROUP)
        self.query_radio = wx.RadioButton(self, label="검색으로 찾기")
        self.all_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode_changed)
        self.query_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode_changed)
        
        top_row1.Add(self.all_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row1.Add(self.query_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # 행 높이 일관성을 위해 시스템 버튼 높이만큼의 Strut 추가
        btn_h = wx.Button.GetDefaultSize().GetHeight()
        top_row1.Add((0, btn_h))
        
        main_sizer.AddSpacer(5)
        main_sizer.Add(top_row1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 2)

        # --- 2. Top Bar: Search (Row 2) ---
        top_row2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.search_input = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_input.SetHint("검색어를 입력하세요(제목/내용)")
        self.search_input.Enable(False)
        self.search_input.Bind(wx.EVT_TEXT_ENTER, self._on_search_clicked)
        
        self.btn_search = wx.Button(self, label="검색")
        self.btn_search.Enable(False)
        self.btn_search.Bind(wx.EVT_BUTTON, self._on_search_clicked)
        
        top_row2.Add(self.search_input, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.btn_search, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # 행 높이 일관성을 위한 Strut
        top_row2.Add((0, btn_h))
        
        main_sizer.Add(top_row2, 0, wx.EXPAND | wx.ALL, 2)

        # --- 2. Template Table (ListCtrl) ---
        self.table = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        cols = ["id", "제목", "수정일"]
        for i, name in enumerate(cols):
            self.table.InsertColumn(i, name, width=0)
            
        self.table.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_table_selection_changed)
        self.table.Bind(wx.EVT_SIZE, self._on_resize)
        
        # User edit: change factor to 3
        main_sizer.Add(self.table, 3, wx.EXPAND | wx.ALL, 5)

        wx.CallAfter(self._set_initial_column_widths)

        # --- 3. Integrated Edit Area ---
        edit_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.title_edit = wx.TextCtrl(self)
        self.title_edit.SetHint("템플릿 제목")
        edit_sizer.Add(self.title_edit, 0, wx.EXPAND | wx.ALL, 2)
        
        self.content_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.content_edit.SetHint("템플릿 내용")
        edit_sizer.Add(self.content_edit, 2, wx.EXPAND | wx.ALL, 2)
        
        # User edit: change factor to 5
        main_sizer.Add(edit_sizer, 5, wx.EXPAND | wx.ALL, 2)

        # --- 4. Control Bar ---
        control_bar = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_memo_save = wx.Button(self, label="메모 저장")
        self.btn_memo_save.Bind(wx.EVT_BUTTON, self._on_save_memo)
        control_bar.Add(self.btn_memo_save, 0, wx.ALL, 2)
        
        control_bar.AddStretchSpacer()
        
        self.btn_edit = wx.Button(self, label="템플릿 수정")
        self.btn_delete = wx.Button(self, label="템플릿 삭제")
        self.btn_recall = wx.Button(self, label="다시 불러오기")
        self.btn_copy = wx.Button(self, label="클립보드로")
        
        self.btn_edit.Bind(wx.EVT_BUTTON, self._on_save_clicked)
        self.btn_delete.Bind(wx.EVT_BUTTON, self._on_delete_clicked)
        self.btn_recall.Bind(wx.EVT_BUTTON, self._on_recall_clicked)
        self.btn_copy.Bind(wx.EVT_BUTTON, self._on_copy_clicked)
        
        control_bar.Add(self.btn_edit, 0, wx.ALL, 2)
        control_bar.Add(self.btn_delete, 0, wx.ALL, 2)
        control_bar.Add(self.btn_recall, 0, wx.ALL, 2)
        control_bar.Add(self.btn_copy, 0, wx.ALL, 2)
        
        main_sizer.Add(control_bar, 0, wx.EXPAND | wx.ALL, 2)

        # --- 5. Memo Area ---
        memo_h_layout = wx.BoxSizer(wx.HORIZONTAL)
        
        self.memo_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.memo_edit.SetHint("여기에 메모를 입력하세요.")
        
        memo_h_layout.Add(self.memo_edit, 1, wx.EXPAND | wx.ALL, 2)
        
        main_sizer.Add(memo_h_layout, 2, wx.EXPAND | wx.ALL, 2)

        self.SetSizer(main_sizer)
        self._refresh_list()

    def _set_initial_column_widths(self):
        """초기 컬럼 너비 설정"""
        self._update_column_widths()

    def _on_resize(self, event):
        """창 크기 변경 시 컬럼 너비 비례 조정"""
        self._update_column_widths()
        event.Skip()

    def _update_column_widths(self):
        """0.1/0.7/0.2 비율로 컬럼 너비 계산"""
        w, _ = self.table.GetClientSize()
        if w <= 0: return
        self.table.SetColumnWidth(0, int(w * 0.1))
        self.table.SetColumnWidth(1, int(w * 0.7))
        self.table.SetColumnWidth(2, int(w * 0.2))

    def _on_mode_changed(self, event):
        is_query = self.query_radio.GetValue()
        self.search_input.Enable(is_query)
        self.btn_search.Enable(is_query)
        if not is_query:
            self._refresh_list()

    def _on_search_clicked(self, event=None):
        query = self.search_input.GetValue().strip()
        if not query:
            self._refresh_list()
            return
        results = self.context.user.search_templates(query)
        self._update_table(results)

    def _refresh_list(self):
        templates = self.context.user.get_all_templates()
        self._update_table(templates)

    def _update_table(self, templates):
        self.table.DeleteAllItems()
        self.current_templates = templates
        
        for i, t in enumerate(templates):
            idx = self.table.InsertItem(self.table.GetItemCount(), str(t['id']))
            self.table.SetItem(idx, 1, t['title'])
            self.table.SetItem(idx, 2, t['modified'])

    def _on_table_selection_changed(self, event):
        idx = self.table.GetFirstSelected()
        if idx == -1 or idx >= len(self.current_templates):
            self._on_clear_selection()
            return
            
        t = self.current_templates[idx]
        self.current_template = t
        
        self.title_edit.ChangeValue(t['title'])
        self.content_edit.ChangeValue(t['text'])
        self.memo_edit.ChangeValue(t.get('memo', '') or "")

    def _on_save_clicked(self, event):
        if not self.current_template:
            wx.MessageBox("수정할 템플릿을 먼저 선택하세요.", "선택 안됨", wx.OK | wx.ICON_WARNING)
            return

        new_title = self.title_edit.GetValue().strip()
        new_text = self.content_edit.GetValue().strip()
        
        if not new_title or not new_text:
            wx.MessageBox("저장할 템플릿의 제목과 내용을 입력하시기 바랍니다.", "내용 입력", wx.OK | wx.ICON_WARNING)
            return

        # 중복 체크: 동일한 제목이 존재하되, 현재 수정 중인 템플릿(ID)이 아닌 경우만 차단
        existing = self.context.user.get_template_by_title(new_title)
        if existing and existing['id'] != self.current_template['id']:
            wx.MessageBox(f"'{new_title}'은(는) 이미 존재하는 제목입니다. 다른 제목을 입력해 주세요.", "알림", wx.OK | wx.ICON_WARNING)
            return
        ret = wx.MessageBox("입력하신 내용으로 템플릿이 수정됩니다.", "수정 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return

        self.context.user.update_template(
            self.current_template['id'],
            new_title,
            new_text,
            self.current_template.get('memo', '') or "" # 기존 메모 유지
        )
        # 메모리 상의 데이터도 동기화
        self.current_template['title'] = new_title
        self.current_template['text'] = new_text
        
        self._refresh_list()

    def _on_delete_clicked(self, event):
        if not self.current_template: return
        ret = wx.MessageBox("선택한 템플릿을 삭제합니다. 이 작업은 취소할 수 없습니다.", "삭제 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return

        self.context.user.delete_template(self.current_template['id'])
        self._on_clear_selection()
        if self.all_radio.GetValue():
            self._refresh_list()
        else:
            self._on_search_clicked()

    def _on_recall_clicked(self, event):
        if not self.current_template: return
        ret = wx.MessageBox("기존에 저장된 템플릿의 내용으로 복원됩니다.", "다시 불러오기", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return
        
        self.title_edit.ChangeValue(self.current_template['title'])
        self.content_edit.ChangeValue(self.current_template['text'])
        self.memo_edit.ChangeValue(self.current_template.get('memo', '') or "")

    def _on_copy_clicked(self, event):
        """본문을 클립보드로 복사"""
        content = self.content_edit.GetValue().strip()
        if content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(content))
                wx.TheClipboard.Close()
                wx.MessageBox("현재 입력된 내용이 클립보드로 복사되었습니다.", "클립보드로 복사", wx.OK | wx.ICON_INFORMATION)

    def _on_save_memo(self, event):
        if not self.current_template: return
        ret = wx.MessageBox("입력하신 내용으로 템플릿 메모가 저장됩니다.", "메모 저장", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return
        
        new_memo = self.memo_edit.GetValue().strip()
        self.context.user.update_template(
            self.current_template['id'],
            self.current_template['title'], # 기존 제목 유지
            self.current_template['text'],  # 기존 본문 유지
            new_memo
        )
        self.current_template['memo'] = new_memo
        
        # 리스트 갱신 (메모 수정사항 반영 목적)
        if self.all_radio.GetValue():
            self._refresh_list()
        else:
            self._on_search_clicked()

    def _on_clear_selection(self):
        self.current_template = None
        self.title_edit.Clear()
        self.content_edit.Clear()
        self.memo_edit.Clear()
        # Deselect in table (tricky in wx)
        for i in range(self.table.GetItemCount()):
             self.table.Select(i, False)
