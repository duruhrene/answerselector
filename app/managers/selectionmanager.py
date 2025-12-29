from typing import Dict, Optional, Any, Callable, List

class SelectionManager:
    """
    사용자의 답변 선택 상태(S1, S2, S3 슬롯)를 메모리에서 관리하는 매니저.
    앱 종료 시 모든 데이터는 휘발됩니다.
    PyQt6 의존성을 제거하고 순수 Python Observer 패턴을 사용합니다.
    """
    def __init__(self):
        # 각 슬롯에 저장될 데이터 구조: {"id": int, "code": str, "text": str}
        self._slots: Dict[str, Optional[Dict[str, Any]]] = {
            "S1": None,
            "S2": None,
            "S3": None
        }
        # 콜백 함수 리스트 (Observer)
        self._observers: List[Callable[[str], None]] = []

    def add_observer(self, callback: Callable[[str], None]):
        """상태 변경 시 호출될 콜백 함수를 등록합니다."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[str], None]):
        """등록된 콜백 함수를 제거합니다."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, slot_name: str):
        """등록된 모든 옵저버에게 변경 사실을 알립니다."""
        for callback in self._observers:
            callback(slot_name)

    def set_slot(self, slot_name: str, data: Dict[str, Any]) -> bool:
        """슬롯에 답변 데이터를 저장합니다."""
        if slot_name in self._slots:
            self._slots[slot_name] = data
            self._notify_observers(slot_name)
            return True
        return False

    def get_slot(self, slot_name: str) -> Optional[Dict[str, Any]]:
        """슬롯의 현재 데이터를 반환합니다."""
        return self._slots.get(slot_name)

    def clear_slot(self, slot_name: str):
        """특정 슬롯을 비웁니다."""
        if slot_name in self._slots:
            self._slots[slot_name] = None
            self._notify_observers(slot_name)

    def clear_all(self):
        """모든 슬롯을 비웁니다."""
        for key in self._slots:
            self._slots[key] = None
            self._notify_observers(key)

    def has_data(self, slot_name: str) -> bool:
        """해당 슬롯에 데이터가 있는지 확인합니다."""
        return self._slots.get(slot_name) is not None
