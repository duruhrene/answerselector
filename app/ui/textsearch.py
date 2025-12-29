import wx
import logging

class TextSearch(wx.Panel):
    """
    키워드 및 문장(임베딩) 검색을 제공하는 탭 (wxPython Native).
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.logger = logging.getLogger("TextSearch")
        self.current_answers = []
        
        self.InitUI()
        self._load_conjunctions()
        self._update_model_status()

    def InitUI(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- 1. Mode & Model Status Bar (Row 1) ---
        top_row1 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.keyword_radio = wx.RadioButton(self, label="단어검색", style=wx.RB_GROUP)
        self.semantic_radio = wx.RadioButton(self, label="문맥으로 검색")
        
        top_row1.Add(self.keyword_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row1.Add(self.semantic_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        top_row1.AddStretchSpacer()
        
        # Model Status
        top_row1.Add(wx.StaticText(self, label="모델 상태 : "), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        self.status_text = wx.StaticText(self, label="로드안됨")
        top_row1.Add(self.status_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # 행 높이 일관성을 위해 시스템 버튼 높이만큼의 Strut 추가
        btn_h = wx.Button.GetDefaultSize().GetHeight()
        top_row1.Add((0, btn_h))
        
        main_sizer.AddSpacer(5)
        main_sizer.Add(top_row1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 2)

        # --- 2. Search Bar (Row 2) ---
        top_row2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.search_input = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_input.SetHint("검색어를 입력하세요...")
        self.search_input.Bind(wx.EVT_TEXT_ENTER, self._on_search_clicked)
        
        self.btn_search = wx.Button(self, label="검색")
        self.btn_search.Bind(wx.EVT_BUTTON, self._on_search_clicked)
        
        self.btn_load_model = wx.Button(self, label="모델 로드")
        self.btn_load_model.Bind(wx.EVT_BUTTON, self._on_load_model_clicked)
        
        self.btn_unload_model = wx.Button(self, label="언로드")
        self.btn_unload_model.Bind(wx.EVT_BUTTON, self._on_unload_model_clicked)

        top_row2.Add(self.search_input, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.btn_search, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.btn_load_model, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.btn_unload_model, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        main_sizer.Add(top_row2, 0, wx.EXPAND | wx.ALL, 2)

        # --- 3. Data Table (ListCtrl) ---
        self.table = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        cols = [
            "code", "대분류", "중분류", "소분류", 
            "제목(민원요지)", "타기관1", "타기관2"
        ]
        for i, name in enumerate(cols):
            self.table.InsertColumn(i, name, width=0)
            
        self.table.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_table_selection_changed)
        self.table.Bind(wx.EVT_SIZE, self._on_resize)

        main_sizer.Add(self.table, 3, wx.EXPAND | wx.ALL, 5)

        wx.CallAfter(self._set_initial_column_widths)

        # --- 4. Selected Answer Text ---
        self.preview_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        main_sizer.Add(self.preview_edit, 5, wx.EXPAND | wx.ALL, 4)

        # --- 5. Control Bar ---
        control_bar = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_memo_save = wx.Button(self, label="메모 저장")
        self.btn_memo_save.Bind(wx.EVT_BUTTON, self._on_save_memo)
        control_bar.Add(self.btn_memo_save, 0, wx.ALL, 2)

        self.conj_combo = wx.Choice(self)
        self.conj_combo.Bind(wx.EVT_CHOICE, self._update_preview)
        control_bar.Add(self.conj_combo, 2, wx.EXPAND | wx.ALL, 2)
        
        control_bar.AddStretchSpacer(1)
        
        self.btn_s1 = wx.Button(self, label="S1로 보냄")
        self.btn_s2 = wx.Button(self, label="S2로 보냄")
        self.btn_s3 = wx.Button(self, label="S3로 보냄")
        self.btn_clear = wx.Button(self, label="초기화")
        
        self.btn_s1.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S1"))
        self.btn_s2.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S2"))
        self.btn_s3.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S3"))
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_clicked)
        
        control_bar.Add(self.btn_s1, 0, wx.ALL, 2)
        control_bar.Add(self.btn_s2, 0, wx.ALL, 2)
        control_bar.Add(self.btn_s3, 0, wx.ALL, 2)
        control_bar.Add(self.btn_clear, 0, wx.ALL, 2)
        
        main_sizer.Add(control_bar, 0, wx.EXPAND | wx.ALL, 2)

        # --- 6. Memo Area ---
        memo_h_layout = wx.BoxSizer(wx.HORIZONTAL)
        
        self.memo_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.memo_edit.SetHint("여기에 메모를 입력하세요.")
        
        memo_h_layout.Add(self.memo_edit, 1, wx.EXPAND | wx.ALL, 2)
        
        main_sizer.Add(memo_h_layout, 2, wx.EXPAND | wx.ALL, 2)

        self.SetSizer(main_sizer)

    def _set_initial_column_widths(self):
        """초기 컬럼 너비 설정"""
        self._update_column_widths()

    def _on_resize(self, event):
        """창 크기 변경 시 컬럼 너비 비례 조정"""
        self._update_column_widths()
        event.Skip()

    def _update_column_widths(self):
        width = self.table.GetClientSize().GetWidth()
        if width <= 0: return

        # 사용자님이 설정하신 비율 유지
        ratios = [0.08, 0.11, 0.11, 0.11, 0.37, 0.11, 0.11]
        for i, ratio in enumerate(ratios):
            self.table.SetColumnWidth(i, int(width * ratio))
    # --- 검색 및 이벤트 핸들링 ---
    def _load_conjunctions(self):
        self.conj_combo.Clear()
        self.conj_combo.Append("접속사 없음", "")
        self.conj_combo.SetSelection(0)
        conjs = self.context.data.get_conjunction_list()
        for c in conjs:
            self.conj_combo.Append(c, c)

    def _update_model_status(self):
        is_loaded = self.context.embed.session is not None
        if is_loaded:
            self.status_text.SetLabel("   로드됨")
            self.btn_load_model.Enable(False)
            self.btn_unload_model.Enable(True)
        else:
            self.status_text.SetLabel("로드안됨")
            self.btn_load_model.Enable(True)
            self.btn_unload_model.Enable(False)

    def _on_load_model_clicked(self, event):
        self.btn_load_model.SetLabel("로딩 중...")
        self.btn_load_model.Enable(False)
        # Force UI update required? wx.Yield() might be needed for instant feedback before blocking op.
        wx.GetApp().Yield()
        
        success = self.context.embed.load_model()
        self.btn_load_model.SetLabel("모델 로드")
        self._update_model_status()

    def _on_unload_model_clicked(self, event):
        self.context.embed.unload_model()
        self._update_model_status()

    def _on_search_clicked(self, event):
        query = self.search_input.GetValue().strip()
        if not query: return

        if self.keyword_radio.GetValue():
            results = self.context.data.search_answers(query)
            self._update_table(results)
        else:
            if self.context.embed.session is None:
                if not self.context.embed.load_model():
                    return
                self._update_model_status()
            
            all_answers = self.context.data.get_all_answers()
            results = self.context.embed.search_similarity(query, all_answers)
            self._update_table(results)

    def _update_table(self, answers):
        self.table.DeleteAllItems()
        self.current_answers = answers
        
        for i, ans in enumerate(answers):
            idx = self.table.InsertItem(self.table.GetItemCount(), str(ans.get("code", "")))
            self.table.SetItem(idx, 1, str(ans.get("cat1", "")))
            self.table.SetItem(idx, 2, str(ans.get("cat2", "")))
            self.table.SetItem(idx, 3, str(ans.get("cat3", "")))
            self.table.SetItem(idx, 4, str(ans.get("title", "")))
            self.table.SetItem(idx, 5, str(ans.get("agency1", "")))
            self.table.SetItem(idx, 6, str(ans.get("agency2", "")))

    def _get_selected_answer(self):
        idx = self.table.GetFirstSelected()
        if idx == -1 or idx >= len(self.current_answers): return None
        return self.current_answers[idx]

    def _on_table_selection_changed(self, event):
        self._update_preview()
        self._load_memo()

    def _update_preview(self, event=None):
        answer = self._get_selected_answer()
        if not answer:
            self.preview_edit.Clear()
            return
            
        conj = ""
        sel_idx = self.conj_combo.GetSelection()
        if sel_idx != wx.NOT_FOUND:
            data = self.conj_combo.GetClientData(sel_idx) # If we used ClientData, but here we appended strings
            # In CatSearch I didn't verify clientData usage.
            # Here I just appended string 'c'. So GetStringSelection is safer if texts are unique.
            conj = self.conj_combo.GetString(sel_idx) 
            if conj == "접속사 없음": conj = ""

        maintext = (answer.get('maintext') or "").replace("\\n", "\n")
        
        agency_info = []
        for key in ["agency1", "agency2"]:
            name = answer.get(key)
            if name:
                agency = self.context.data.get_agency(name)
                if agency:
                    tel = agency.get('tel') or ""
                    paid = agency.get('paid') or ""
                    website = agency.get('website') or ""
                    tel_paid = f"{tel}{paid}"
                    
                    if tel_paid and website:
                        info = f"※ {name}({tel_paid}, {website})"
                    elif tel_paid:
                        info = f"※ {name}({tel_paid})"
                    elif website:
                        info = f"※ {name}({website})"
                    else:
                        info = f"※ {name}"
                    agency_info.append(info)
        
        res = ""
        if conj: res += conj
        res += maintext
        if agency_info:
            res += "\n" + "\n".join(agency_info)
        self.preview_edit.ChangeValue(res.strip())

    def _load_memo(self):
        answer = self._get_selected_answer()
        if not answer:
            self.memo_edit.Clear()
            return
        ans_id = answer.get("id")
        memo = self.context.user.get_answer_memo(ans_id)
        self.memo_edit.ChangeValue(memo or "")

    def _on_save_memo(self, event):
        answer = self._get_selected_answer()
        if not answer: return
        ret = wx.MessageBox("입력하신 내용으로 메모가 저장됩니다.", "메모 저장", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return
        
        ans_id = answer.get("id")
        memo = self.memo_edit.GetValue().strip()
        self.context.user.save_answer_memo(ans_id, memo)

    def _send_to_slot(self, slot_name):
        answer = self._get_selected_answer()
        if not answer: return
        text = self.preview_edit.GetValue().strip()
        if not text: return
        
        ret = wx.MessageBox(f"현재 선택(조합)된 내용을 {slot_name}로 보냅니다.", "슬롯으로 전송", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return

        data = {"id": answer.get("id"), "code": answer.get("code"), "text": text}
        self.context.selection.set_slot(slot_name, data)

    def _on_clear_clicked(self, event):
        ret = wx.MessageBox("선택하신 내용이 모두 초기화됩니다.", "초기화 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return
        
        self.search_input.Clear()
        self.table.DeleteAllItems()
        self.preview_edit.Clear()
        self.memo_edit.Clear()
        self.conj_combo.SetSelection(0)
