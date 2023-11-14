from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit


class SubLineEdit(QLineEdit):
    def __init__(
        self, on_backspace_at_start, on_enter_in_middle, on_delete_at_end, parent=None
    ):
        super().__init__(parent)
        self.on_backspace_at_start = on_backspace_at_start
        self.on_enter_in_middle = on_enter_in_middle
        self.on_delete_at_end = on_delete_at_end

    def keyPressEvent(self, event):
        widget = self.focusWidget()
        if event.key() == Qt.Key_Backspace and self.cursorPosition() == 0:
            self.on_backspace_at_start(widget)
        elif event.key() == Qt.Key_Return and self.cursorPosition() != len(self.text()):
            self.on_enter_in_middle(widget)
        elif event.key() == Qt.Key_Delete and self.cursorPosition() == len(self.text()):
            self.on_delete_at_end(widget)
        else:
            super().keyPressEvent(event)
