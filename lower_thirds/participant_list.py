from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFrame,
    QListWidget,
    QListWidgetItem,
)


class ParticipantListWidget(QListWidget):
    """List widget that reorders via data updates instead of Qt internal moves."""

    reordered = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSpacing(4)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._source_row = -1

        self._drop_indicator = QFrame(self.viewport())
        self._drop_indicator.setFixedHeight(2)
        self._drop_indicator.setStyleSheet("background-color: #4a90d9; border: none;")
        self._drop_indicator.hide()

    def start_row_drag(self, item: QListWidgetItem) -> None:
        self._source_row = self.row(item)
        if self._source_row < 0:
            return

        self.setCurrentItem(item)
        drag = QDrag(self)
        drag.setMimeData(self.model().mimeData([self.indexFromItem(item)]))
        drag.exec(Qt.DropAction.MoveAction)
        self._source_row = -1
        self._hide_drop_indicator()

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.source() is self:
            event.acceptProposedAction()
            self._update_drop_indicator(event.position().toPoint())
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.source() is self:
            event.acceptProposedAction()
            self._update_drop_indicator(event.position().toPoint())
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._hide_drop_indicator()

        source_row = self._source_row
        if source_row < 0 or event.source() is not self:
            event.ignore()
            return

        viewport_pos = self._viewport_position(event.position().toPoint())
        target_row = self._target_row_from_position(viewport_pos)
        if source_row < target_row:
            target_row -= 1

        event.acceptProposedAction()
        self._source_row = -1

        if source_row != target_row:
            self.reordered.emit(source_row, target_row)

    def _viewport_position(self, position) -> object:
        return self.viewport().mapFrom(self, position)

    def _update_drop_indicator(self, position) -> None:
        viewport_pos = self._viewport_position(position)
        drop_row = self._target_row_from_position(viewport_pos)
        indicator_y = self._indicator_y(drop_row)
        if indicator_y is None:
            self._hide_drop_indicator()
            return

        self._drop_indicator.setGeometry(0, indicator_y - 1, self.viewport().width(), 2)
        self._drop_indicator.show()
        self._drop_indicator.raise_()

    def _hide_drop_indicator(self) -> None:
        self._drop_indicator.hide()

    def _indicator_y(self, drop_row: int) -> int | None:
        if self.count() == 0:
            return 0

        if drop_row <= 0:
            item = self.item(0)
            return self.visualItemRect(item).top() if item is not None else 0

        if drop_row >= self.count():
            item = self.item(self.count() - 1)
            return self.visualItemRect(item).bottom() if item is not None else None

        item = self.item(drop_row)
        if item is None:
            return None
        return self.visualItemRect(item).top()

    def _target_row_from_position(self, position) -> int:
        for row in range(self.count()):
            item = self.item(row)
            if item is None:
                continue
            rect = self.visualItemRect(item)
            if position.y() < rect.center().y():
                return row
        return self.count()


class DragHandleFilter(QObject):
    """Starts a list drag from the handle, since item widgets block default dragging."""

    def __init__(self, list_widget: ParticipantListWidget, item: QListWidgetItem) -> None:
        super().__init__(list_widget)
        self._list_widget = list_widget
        self._item = item
        self._drag_start_pos = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        del watched
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            mouse_event = event
            if isinstance(mouse_event, QMouseEvent):
                self._drag_start_pos = mouse_event.globalPosition().toPoint()
            self._list_widget.setCurrentItem(self._item)
            return False

        if (
            event.type() == QEvent.Type.MouseMove
            and self._drag_start_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            mouse_event = event
            if isinstance(mouse_event, QMouseEvent):
                distance = (mouse_event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
                if distance >= QApplication.startDragDistance():
                    self._list_widget.start_row_drag(self._item)
                    self._drag_start_pos = None
                    return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            self._drag_start_pos = None

        return False
