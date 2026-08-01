from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from lower_thirds.data_store import DataStore
from lower_thirds.models import Participant


class LowerThirdBar(QWidget):
    """Lower-third banner with name, title, and subtitle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._style = DataStore.LOWER_THIRD_STYLE_DEFAULT
        self._background_pixmap = QPixmap()
        self._bar_color = QColor(DataStore.DEFAULT_LOWER_THIRD_BAR_COLOR)
        self._accent_color = QColor(DataStore.DEFAULT_LOWER_THIRD_ACCENT_COLOR)

        self.name_label = QLabel(self)
        self.title_label = QLabel(self)
        self.subtitle_label = QLabel(self)

        for label in (self.name_label, self.title_label, self.subtitle_label):
            label.setStyleSheet("color: white; background: transparent; border: none;")

        self.name_label.setFont(QFont("Sans Serif", 24, QFont.Weight.Bold))
        self.title_label.setFont(QFont("Sans Serif", 14))
        self.subtitle_label.setFont(QFont("Sans Serif", 12))
        self.subtitle_label.setStyleSheet("color: #d0d0d0; background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 14, 28, 14)
        layout.setSpacing(2)
        layout.addWidget(self.name_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        self.setFixedHeight(110)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.hide()

    def set_style(self, style: str, background_path: Path | None = None) -> None:
        self._style = style
        self._background_pixmap = QPixmap()

        if style == DataStore.LOWER_THIRD_STYLE_CUSTOM and background_path is not None:
            pixmap = QPixmap(str(background_path))
            if not pixmap.isNull():
                self._background_pixmap = pixmap
                height = max(110, int(110 * (pixmap.height() / max(pixmap.width(), 1))))
                self.setFixedHeight(min(height, 220))

        if self._background_pixmap.isNull():
            self._style = DataStore.LOWER_THIRD_STYLE_DEFAULT
            self.setFixedHeight(110)

        self.update()

    def set_default_appearance(self, bar_color: str, accent_color: str) -> None:
        parsed_bar = QColor(bar_color)
        parsed_accent = QColor(accent_color)
        if parsed_bar.isValid():
            parsed_bar.setAlpha(255)
            self._bar_color = parsed_bar
        if parsed_accent.isValid():
            parsed_accent.setAlpha(255)
            self._accent_color = parsed_accent
        self.update()

    def _opaque_accent_color(self) -> QColor:
        color = QColor(self._accent_color)
        color.setAlpha(255)
        return color

    def set_participant(self, participant: Participant | None) -> None:
        if participant is None:
            self.name_label.clear()
            self.title_label.clear()
            self.subtitle_label.clear()
            return

        self.name_label.setText(participant.name)
        self.title_label.setText(participant.title)
        self.title_label.setVisible(bool(participant.title.strip()))
        self.subtitle_label.setText(participant.subtitle)
        self.subtitle_label.setVisible(bool(participant.subtitle.strip()))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        if self._style == DataStore.LOWER_THIRD_STYLE_CUSTOM and not self._background_pixmap.isNull():
            scaled = self._background_pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(rect.topLeft(), scaled)
        else:
            accent_width = 8
            painter.fillRect(rect.adjusted(accent_width, 0, 0, 0), self._bar_color)
            painter.fillRect(0, 0, accent_width, rect.height(), self._opaque_accent_color())

        super().paintEvent(event)


class LowerThirdDisplay(QWidget):
    """Preview area at the bottom of the main window."""

    MARGIN = 16

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(130)

        self.lower_third = LowerThirdBar(self)
        self._slide_animation: QPropertyAnimation | None = None
        self._active_participant_id: str | None = None
        self._background_color = QColor("#00ff00")
        self.set_background_color(self._background_color)

    def set_lower_third_style(self, style: str, background_path: Path | None = None) -> None:
        self.lower_third.set_style(style, background_path)
        if self._slide_animation is None or self._slide_animation.state() != QPropertyAnimation.State.Running:
            bar_width = max(360, self.width() - self.MARGIN * 2)
            self.lower_third.setFixedWidth(bar_width)
            x = self._rest_x() if self._active_participant_id else self._hidden_x()
            self._position_bar(x)

    def set_default_lower_third_appearance(self, bar_color: str, accent_color: str) -> None:
        self.lower_third.set_default_appearance(bar_color, accent_color)

    def set_background_color(self, color: QColor | str) -> None:
        if isinstance(color, str):
            parsed = QColor(color)
            if not parsed.isValid():
                return
            color = parsed

        self._background_color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._background_color)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#aaaaaa"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    def resizeEvent(self, event) -> None:  # noqa: N802
        bar_width = max(360, self.width() - self.MARGIN * 2)
        self.lower_third.setFixedWidth(bar_width)
        if self._slide_animation is None or self._slide_animation.state() != QPropertyAnimation.State.Running:
            x = self._rest_x() if self._active_participant_id else self._hidden_x()
            self._position_bar(x)
        super().resizeEvent(event)

    def _bar_y(self) -> int:
        return (self.height() - self.lower_third.height()) // 2

    def _rest_x(self) -> int:
        return self.MARGIN

    def _hidden_x(self) -> int:
        return -self.lower_third.width()

    def _position_bar(self, x: int | None = None) -> None:
        if x is None:
            x = self._rest_x() if self._active_participant_id else self._hidden_x()
        self.lower_third.move(x, self._bar_y())

    def show_participant(self, participant: Participant) -> None:
        self._active_participant_id = participant.id
        self.lower_third.set_participant(participant)
        self.lower_third.show()
        self._animate_in()

    def hide_lower_third(self) -> None:
        self._active_participant_id = None
        self._animate_out()

    def is_showing(self, participant_id: str) -> bool:
        return self._active_participant_id == participant_id

    def has_active_participant(self) -> bool:
        return self._active_participant_id is not None

    def _animate_in(self) -> None:
        self._stop_animations()
        y = self._bar_y()
        self.lower_third.move(self._hidden_x(), y)

        self._slide_animation = QPropertyAnimation(self.lower_third, b"pos")
        self._slide_animation.setDuration(350)
        self._slide_animation.setStartValue(self.lower_third.pos())
        self._slide_animation.setEndValue(QPoint(self._rest_x(), y))
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_animation.start()

    def _animate_out(self) -> None:
        self._stop_animations()
        y = self._bar_y()

        self._slide_animation = QPropertyAnimation(self.lower_third, b"pos")
        self._slide_animation.setDuration(250)
        self._slide_animation.setStartValue(self.lower_third.pos())
        self._slide_animation.setEndValue(QPoint(self._hidden_x(), y))
        self._slide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide_animation.finished.connect(self._on_hide_finished)
        self._slide_animation.start()

    def _on_hide_finished(self) -> None:
        self.lower_third.hide()
        self.lower_third.set_participant(None)
        self._slide_animation = None

    def _stop_animations(self) -> None:
        if self._slide_animation is None:
            return

        animation = self._slide_animation
        self._slide_animation = None
        try:
            animation.finished.disconnect(self._on_hide_finished)
        except TypeError:
            pass
        animation.stop()
