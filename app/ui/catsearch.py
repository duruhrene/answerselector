import wx
import logging

class CatSearch(wx.Panel):
    """
    와이어프레임을 충실히 반영한 카테고리 검색 탭 (wxPython Native).
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.logger = logging.getLogger("CatSearch")
        self.current_answers = [] # 현재 테이블에 로드된 원본 데이터
        
        self.InitUI()
        self._load_cat1_initial()
        self._load_conjunctions()
        
        # 초기 상태: '카테고리로 찾기' 모드, 첫 번째 대분류 선택
        self.cat_radio.SetValue(True)
        self._on_mode_changed(None)

    def InitUI(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- 1. Top Bar: Mode Radio Buttons (Row 1) ---
        top_row1 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.all_radio = wx.RadioButton(self, label="전체보기", style=wx.RB_GROUP)
        self.cat_radio = wx.RadioButton(self, label="카테고리로 찾기")
        
        self.all_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode_changed)
        self.cat_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode_changed)
        
        top_row1.Add(self.all_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row1.Add(self.cat_radio, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # 행 높이 일관성을 위해 시스템 버튼 높이만큼의 Strut 추가
        btn_h = wx.Button.GetDefaultSize().GetHeight()
        top_row1.Add((0, btn_h))
        
        main_sizer.AddSpacer(5)
        main_sizer.Add(top_row1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 2)

        # --- 2. Selection Bar: Cat1, Cat2, Cat3 (Row 2) ---
        top_row2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.cat1_combo = wx.Choice(self)
        self.cat2_combo = wx.Choice(self)
        self.cat3_combo = wx.Choice(self)
        
        self.cat1_combo.Bind(wx.EVT_CHOICE, self._on_cat1_changed)
        self.cat2_combo.Bind(wx.EVT_CHOICE, self._on_cat2_changed)
        self.cat3_combo.Bind(wx.EVT_CHOICE, self._on_cat3_changed)
        
        # 3개의 콤보박스를 균등하게 배치 (비율 1:1:1)
        top_row2.Add(self.cat1_combo, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.cat2_combo, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        top_row2.Add(self.cat3_combo, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        
        # 행 높이 일관성
        top_row2.Add((0, btn_h))
        
        main_sizer.Add(top_row2, 0, wx.EXPAND | wx.ALL, 2)

        # --- 3. Data Table (ListCtrl) ---
        # code, 대분류, 중분류, 소분류, 제목(민원요지), 타기관1, 타기관2
        self.table = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        cols = [
            "code", "대분류", "중분류", "소분류", 
            "제목(민원요지)", "타기관1", "타기관2"
        ]
        for i, name in enumerate(cols):
            self.table.InsertColumn(i, name, width=0) # 초기 너비 0 (비율로 자동 조정됨)
        
        self.table.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_table_selection_changed)
        self.table.Bind(wx.EVT_SIZE, self._on_resize)
        
        main_sizer.Add(self.table, 3, wx.EXPAND | wx.ALL, 5)

        wx.CallAfter(self._set_initial_column_widths)

        # --- 4. Selected Answer Text (Preview) ---
        self.preview_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        main_sizer.Add(self.preview_edit, 5, wx.EXPAND | wx.ALL, 4)

        # --- 5. Control Bar: Conjunction & Send Buttons ---
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
        self.btn_clear_slots = wx.Button(self, label="초기화")
        
        self.btn_s1.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S1"))
        self.btn_s2.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S2"))
        self.btn_s3.Bind(wx.EVT_BUTTON, lambda evt: self._send_to_slot("S3"))
        self.btn_clear_slots.Bind(wx.EVT_BUTTON, self._on_clear_selection)
        
        control_bar.Add(self.btn_s1, 0, wx.ALL, 2)
        control_bar.Add(self.btn_s2, 0, wx.ALL, 2)
        control_bar.Add(self.btn_s3, 0, wx.ALL, 2)
        control_bar.Add(self.btn_clear_slots, 0, wx.ALL, 2)
        
        main_sizer.Add(control_bar, 0, wx.EXPAND | wx.ALL, 2)

        # --- 6. Memo Area ---
        memo_h_layout = wx.BoxSizer(wx.HORIZONTAL)
        
        self.memo_edit = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.memo_edit.SetHint("여기에 메모를 입력하세요.")
        
        memo_h_layout.Add(self.memo_edit, 1, wx.EXPAND | wx.ALL, 2)
        
        main_sizer.Add(memo_h_layout, 2, wx.EXPAND | wx.ALL, 2) # 버튼 레이아웃 제거하고 바로 추가

        self.SetSizer(main_sizer)

    def _set_initial_column_widths(self):
        """초기 컬럼 너비 설정"""
        self._update_column_widths()

    def _on_resize(self, event):
        self._update_column_widths()
        event.Skip()

    def _update_column_widths(self):
        width = self.table.GetClientSize().GetWidth()
        if width <= 0: return

        # 사용자님이 설정하신 비율 유지
        ratios = [0.08, 0.11, 0.11, 0.11, 0.37, 0.11, 0.11]
        for i, ratio in enumerate(ratios):
            self.table.SetColumnWidth(i, int(width * ratio))

    # --- Data Loading ---
    def _load_cat1_initial(self):
        self.cat1_combo.Clear()
        self.cat1_combo.Append("대분류 선택", None)
        cats = self.context.data.get_cat1_list()
        for c in cats:
            self.cat1_combo.Append(c, c)
        self.cat1_combo.SetSelection(0)

    def _load_conjunctions(self):
        self.conj_combo.Clear()
        self.conj_combo.Append("접속사 없음", "")
        self.conj_combo.SetSelection(0)
        
        conjs = self.context.data.get_conjunction_list()
        for c in conjs:
            self.conj_combo.Append(c, c)

    # --- Mode & Selection Logic ---
    def _on_mode_changed(self, event):
        is_all = self.all_radio.GetValue()
        
        # 콤보박스 활성/비활성 처리
        self.cat1_combo.Enable(not is_all)
        self.cat2_combo.Enable(not is_all)
        self.cat3_combo.Enable(not is_all)
        
        if is_all:
            # 전체 보기 모드: 모든 답변 로드
            all_answers = self.context.data.get_all_answers()
            self._update_table(all_answers)
            # 콤보박스 선택은 시각적으로 초기화해주는 것이 좋음
            self.cat1_combo.SetSelection(wx.NOT_FOUND)
            self.cat2_combo.Clear()
            self.cat3_combo.Clear()
        else:
            # 카테고리 모드: 리스트 초기화하고 콤보박스 선택 유도
            self.table.DeleteAllItems()
            # 만약 cat1이 선택되어 있지 않다면 첫 번째 항목 자동 선택
            if self.cat1_combo.GetCount() > 0 and self.cat1_combo.GetSelection() == wx.NOT_FOUND:
                self.cat1_combo.SetSelection(0)
                self._on_cat1_changed(None)

    def _on_cat1_changed(self, event):
        # Handle Placeholder
        if self.cat1_combo.GetSelection() == 0:
            cat1 = None
        else:
            cat1 = self.cat1_combo.GetStringSelection()
        
        self.cat2_combo.Clear()
        self.cat2_combo.Append("중분류 선택", None) # Placeholder
        self.cat2_combo.SetSelection(0)
        
        if cat1:
            cats = self.context.data.get_cat2_list(cat1)
            for c in cats:
                self.cat2_combo.Append(c, c)
            
        self.cat3_combo.Clear()
        self.table.DeleteAllItems()
        self.preview_edit.Clear()
        self.memo_edit.Clear()

    def _on_cat2_changed(self, event):
        cat1 = self.cat1_combo.GetStringSelection()
        
        # Placeholder 체크
        if self.cat2_combo.GetSelection() == 0:
            cat2 = None
        else:
            cat2 = self.cat2_combo.GetStringSelection()

        self.cat3_combo.Clear()
        self.cat3_combo.Append("소분류 선택", None) # Placeholder
        self.cat3_combo.SetSelection(0)
        
        if cat1 and cat2:
            cats = self.context.data.get_cat3_list(cat2, cat1)
            for c in cats:
                self.cat3_combo.Append(c, c)
                
        self.table.DeleteAllItems()

    def _on_cat3_changed(self, event):
        cat1 = self.cat1_combo.GetStringSelection()
        
        # Cat2 (Placeholder check)
        if self.cat2_combo.GetSelection() == 0:
            cat2 = None
        else:
            cat2 = self.cat2_combo.GetStringSelection()
        
        # Cat3 (Placeholder check)
        if self.cat3_combo.GetSelection() == 0:
            cat3 = None
        else:
            cat3 = self.cat3_combo.GetStringSelection()
        
        if cat1 and cat2 and cat3:
            answers = self.context.data.get_answers_in_cat3(cat2, cat3, cat1)
            self._update_table(answers)
        else:
            self.table.DeleteAllItems()

    def _update_table(self, answers):
        self.table.DeleteAllItems()
        self.current_answers = answers # Keep reference if needed
        # ListCtrl.Data is a good place to store the object
        
        for ans in answers:
            # InsertItem returns index
            idx = self.table.InsertItem(self.table.GetItemCount(), str(ans.get("code", "")))
            self.table.SetItem(idx, 1, str(ans.get("cat1", "")))
            self.table.SetItem(idx, 2, str(ans.get("cat2", "")))
            self.table.SetItem(idx, 3, str(ans.get("cat3", "")))
            self.table.SetItem(idx, 4, str(ans.get("title", "")))
            self.table.SetItem(idx, 5, str(ans.get("agency1", "")))
            self.table.SetItem(idx, 6, str(ans.get("agency2", "")))
            
            # Store full data object in item data
            # (Deleted implementation notes)

    def _get_selected_answer(self):
        idx = self.table.GetFirstSelected()
        if idx == -1:
            return None
        if idx < len(self.current_answers):
            return self.current_answers[idx]
        return None

    def _on_table_selection_changed(self, event):
        self._update_preview(None)
        self._load_memo()

    def _update_preview(self, event=None):
        answer = self._get_selected_answer()
        if not answer:
            self.preview_edit.Clear()
            return
            
        # Conj
        sel_idx = self.conj_combo.GetSelection()
        conj = ""
        if sel_idx != wx.NOT_FOUND:
            data = self.conj_combo.GetClientData(sel_idx)
            if data: conj = data

        maintext = (answer.get('maintext') or "").replace("\\n", "\n")
        
        # Agency
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

        data = {
            "id": answer.get("id"),
            "code": answer.get("code"),
            "text": text
        }
        self.context.selection.set_slot(slot_name, data)

    def _on_clear_selection(self, event):
        ret = wx.MessageBox("선택하신 내용이 모두 초기화됩니다.", "초기화 확인", wx.YES_NO | wx.ICON_QUESTION)
        if ret == wx.NO: return

        self.cat_radio.SetValue(True)
        self.all_radio.SetValue(False)
        self._on_mode_changed(None)
        self.conj_combo.SetSelection(0)
