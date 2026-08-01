from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

from lower_thirds.data_store import DataStore
from lower_thirds.lower_third_display import LowerThirdDisplay
from lower_thirds.models import Participant
from lower_thirds.participant_list import DragHandleFilter, ParticipantListWidget


class ParticipantDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        participant: Participant | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Participant" if participant else "Add Participant")

        self.name_input = QLineEdit(participant.name if participant else "")
        self.title_input = QLineEdit(participant.title if participant else "")
        self.subtitle_input = QLineEdit(participant.subtitle if participant else "")

        form = QFormLayout()
        form.addRow("Name", self.name_input)
        form.addRow("Title", self.title_input)
        form.addRow("Subtitle", self.subtitle_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._participant = participant

    def get_participant(self) -> Participant | None:
        name = self.name_input.text().strip()
        if not name:
            return None

        if self._participant is None:
            return Participant(
                name=name,
                title=self.title_input.text().strip(),
                subtitle=self.subtitle_input.text().strip(),
            )

        self._participant.name = name
        self._participant.title = self.title_input.text().strip()
        self._participant.subtitle = self.subtitle_input.text().strip()
        return self._participant


class ParticipantRow(QWidget):
    show_requested = pyqtSignal(str)
    hide_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, participant: Participant, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.participant_id = participant.id

        drag_handle = QLabel("⋮⋮")
        drag_handle.setFixedWidth(20)
        drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_handle.setStyleSheet("color: #888;")
        drag_handle.setToolTip("Drag to reorder")
        drag_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self.drag_handle = drag_handle

        name_label = QLabel(participant.name)
        name_label.setStyleSheet("font-weight: bold;")
        detail_parts = [part for part in (participant.title, participant.subtitle) if part]
        detail_label = QLabel(" · ".join(detail_parts) if detail_parts else "No title")
        detail_label.setStyleSheet("color: #666;")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(name_label)
        text_layout.addWidget(detail_label)

        show_button = QPushButton("Show")
        show_button.clicked.connect(lambda: self.show_requested.emit(self.participant_id))

        hide_button = QPushButton("Turn Off")
        hide_button.clicked.connect(self.hide_requested.emit)

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self.participant_id))

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self.participant_id))

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(show_button)
        actions.addWidget(hide_button)
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        actions.addStretch()

        layout = QHBoxLayout(self)
        layout.addWidget(drag_handle)
        layout.addLayout(text_layout, stretch=1)
        layout.addLayout(actions)


class MainWindow(QMainWindow):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store

        self.setWindowTitle("Lower Thirds")
        self.resize(900, 650)

        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #666;")

        self.participant_list = ParticipantListWidget()
        self.participant_list.reordered.connect(self._move_participant)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_lower_third)

        self.lower_third_display = LowerThirdDisplay()

        self.preview_color_swatch = QLabel()
        self.preview_color_swatch.setFixedSize(28, 28)
        self.preview_color_swatch.setToolTip("Current chroma key background color")

        preview_color_button = QPushButton("Choose Background…")
        preview_color_button.clicked.connect(self.choose_preview_background)

        green_button = QPushButton("Green")
        green_button.clicked.connect(lambda: self.set_preview_background("#00ff00"))

        magenta_button = QPushButton("Magenta")
        magenta_button.clicked.connect(lambda: self.set_preview_background("#ff00ff"))

        blue_button = QPushButton("Blue")
        blue_button.clicked.connect(lambda: self.set_preview_background("#0000ff"))

        preview_controls = QHBoxLayout()
        preview_controls.addWidget(QLabel("Chroma background:"))
        preview_controls.addWidget(self.preview_color_swatch)
        preview_controls.addWidget(preview_color_button)
        preview_controls.addWidget(green_button)
        preview_controls.addWidget(magenta_button)
        preview_controls.addWidget(blue_button)
        preview_controls.addStretch()

        self.display_duration_spin = QSpinBox()
        self.display_duration_spin.setRange(0, 3600)
        self.display_duration_spin.setSuffix(" s")
        self.display_duration_spin.setToolTip(
            "Automatically hide the lower third after this many seconds (0 = stay on)"
        )
        self.display_duration_spin.valueChanged.connect(self._on_display_duration_changed)

        timer_controls = QHBoxLayout()
        timer_controls.addWidget(QLabel("Auto-hide after:"))
        timer_controls.addWidget(self.display_duration_spin)
        timer_controls.addStretch()

        self.lower_third_style_combo = QComboBox()
        self.lower_third_style_combo.addItem(
            "Default",
            DataStore.LOWER_THIRD_STYLE_DEFAULT,
        )
        self.lower_third_style_combo.addItem(
            "Custom background",
            DataStore.LOWER_THIRD_STYLE_CUSTOM,
        )
        self.lower_third_style_combo.currentIndexChanged.connect(
            self._on_lower_third_style_changed
        )

        self.import_lower_third_button = QPushButton("Import Background…")
        self.import_lower_third_button.clicked.connect(self.import_lower_third_background)

        self.lower_third_style_label = QLabel()
        self.lower_third_style_label.setStyleSheet("color: #666;")

        style_controls = QHBoxLayout()
        style_controls.addWidget(QLabel("Lower third style:"))
        style_controls.addWidget(self.lower_third_style_combo)
        style_controls.addWidget(self.import_lower_third_button)
        style_controls.addWidget(self.lower_third_style_label, stretch=1)

        self.bar_color_swatch = QLabel()
        self.bar_color_swatch.setFixedSize(28, 28)
        self.bar_color_button = QPushButton("Bar Color…")
        self.bar_color_button.clicked.connect(self.choose_lower_third_bar_color)

        self.accent_color_swatch = QLabel()
        self.accent_color_swatch.setFixedSize(28, 28)
        self.accent_color_button = QPushButton("Accent Color…")
        self.accent_color_button.clicked.connect(self.choose_lower_third_accent_color)

        self._default_appearance_widgets = (
            self.bar_color_swatch,
            self.bar_color_button,
            self.accent_color_swatch,
            self.accent_color_button,
        )

        appearance_controls = QHBoxLayout()
        appearance_controls.addWidget(QLabel("Default appearance:"))
        appearance_controls.addWidget(self.bar_color_swatch)
        appearance_controls.addWidget(self.bar_color_button)
        appearance_controls.addWidget(self.accent_color_swatch)
        appearance_controls.addWidget(self.accent_color_button)
        appearance_controls.addStretch()

        open_button = QPushButton("Open JSON…")
        open_button.clicked.connect(self.open_file)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_file)

        save_as_button = QPushButton("Save As…")
        save_as_button.clicked.connect(self.save_file_as)

        add_button = QPushButton("Add Participant")
        add_button.clicked.connect(self.add_participant)

        file_actions = QHBoxLayout()
        file_actions.addWidget(open_button)
        file_actions.addWidget(save_button)
        file_actions.addWidget(save_as_button)
        file_actions.addStretch()

        participant_actions = QHBoxLayout()
        participant_actions.addWidget(add_button)
        participant_actions.addStretch()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.file_label)
        layout.addLayout(file_actions)
        layout.addLayout(participant_actions)
        layout.addWidget(self.participant_list, stretch=1)
        layout.addLayout(timer_controls)
        layout.addLayout(style_controls)
        layout.addLayout(appearance_controls)
        layout.addLayout(preview_controls)
        layout.addWidget(self.lower_third_display)
        self.setCentralWidget(container)

        style, background = self._load_lower_third_style_settings()
        self.store.lower_third_style = style
        self.store.lower_third_background = background
        self.apply_preview_background(self._load_preview_background())
        self.apply_display_duration(self._load_display_duration())
        self.apply_default_lower_third_appearance(self._load_default_appearance_settings())
        self.apply_lower_third_style()
        self._restore_last_json_file()
        self.refresh_participant_list()

    def _settings(self) -> QSettings:
        return QSettings("lower-thirds", "lower-thirds")

    def _last_json_file_path(self) -> Path | None:
        value = self._settings().value("last_json_file", "", type=str)
        if not value:
            return None
        return Path(value)

    def _save_last_json_file(self, path: Path) -> None:
        self._settings().setValue("last_json_file", str(path))

    def _default_json_directory(self) -> str:
        last_path = self._last_json_file_path()
        if last_path is not None:
            return str(last_path.parent)
        if self.store.file_path is not None:
            return str(self.store.file_path.parent)
        return str(Path.home())

    def _default_save_path(self) -> str:
        if self.store.file_path is not None:
            return str(self.store.file_path)
        last_path = self._last_json_file_path()
        if last_path is not None:
            return str(last_path)
        return str(Path.home() / "lower-thirds.json")

    def _load_json_file(self, path: Path, *, show_errors: bool = True) -> bool:
        try:
            self.store.load(path)
        except (OSError, ValueError) as exc:
            if show_errors:
                QMessageBox.critical(self, "Open Failed", str(exc))
            return False

        self.apply_preview_background(self.store.preview_background)
        self._save_preview_background(self.store.preview_background)
        self.apply_display_duration(self.store.display_duration_seconds)
        self._save_display_duration(self.store.display_duration_seconds)
        self.apply_default_lower_third_appearance()
        self._save_default_appearance_settings()
        self.apply_lower_third_style()
        self._save_lower_third_style_settings()
        self._save_last_json_file(path)
        return True

    def _restore_last_json_file(self) -> bool:
        path = self._last_json_file_path()
        if path is None or not path.is_file():
            return False
        return self._load_json_file(path, show_errors=False)

    def refresh_participant_list(self) -> None:
        self.participant_list.clear()
        for participant in self.store.participants:
            item = QListWidgetItem(self.participant_list)
            item.setData(Qt.ItemDataRole.UserRole, participant.id)
            row = ParticipantRow(participant)
            row.show_requested.connect(self.show_participant)
            row.hide_requested.connect(self.hide_lower_third)
            row.edit_requested.connect(self.edit_participant)
            row.delete_requested.connect(self.delete_participant)
            item.setSizeHint(row.sizeHint())
            self.participant_list.addItem(item)
            self.participant_list.setItemWidget(item, row)
            row.drag_handle.installEventFilter(DragHandleFilter(self.participant_list, item))

        if self.store.file_path:
            self.file_label.setText(str(self.store.file_path))
        else:
            self.file_label.setText("No file loaded — save to choose a location")

    def _move_participant(self, from_index: int, to_index: int) -> None:
        if not self.store.move_participant(from_index, to_index):
            self.refresh_participant_list()
            return
        self.refresh_participant_list()

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Lower Thirds Data",
            self._default_json_directory(),
            "JSON Files (*.json)",
        )
        if not path:
            return

        if self._load_json_file(Path(path)):
            self.refresh_participant_list()

    def save_file(self) -> None:
        if self.store.file_path is None:
            self.save_file_as()
            return

        try:
            self.store.save()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return

        self._save_last_json_file(self.store.file_path)
        self.refresh_participant_list()

    def save_file_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Lower Thirds Data",
            self._default_save_path(),
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            saved_path = self.store.save(Path(path))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return

        self._save_last_json_file(saved_path)
        self.refresh_participant_list()

    def add_participant(self) -> None:
        dialog = ParticipantDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        participant = dialog.get_participant()
        if participant is None:
            QMessageBox.warning(self, "Missing Name", "Participant name is required.")
            return

        self.store.add_participant(participant)
        self.refresh_participant_list()

    def edit_participant(self, participant_id: str) -> None:
        participant = self.store.get_participant(participant_id)
        if participant is None:
            return

        dialog = ParticipantDialog(self, participant)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        updated = dialog.get_participant()
        if updated is None:
            QMessageBox.warning(self, "Missing Name", "Participant name is required.")
            return

        self.store.update_participant(updated)
        if self.lower_third_display.is_showing(participant_id):
            self.show_participant(participant_id)
        self.refresh_participant_list()

    def delete_participant(self, participant_id: str) -> None:
        participant = self.store.get_participant(participant_id)
        if participant is None:
            return

        answer = QMessageBox.question(
            self,
            "Delete Participant",
            f'Delete "{participant.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if self.lower_third_display.is_showing(participant_id):
            self.lower_third_display.hide_lower_third()

        self.store.remove_participant(participant_id)
        self.refresh_participant_list()

    def show_participant(self, participant_id: str) -> None:
        participant = self.store.get_participant(participant_id)
        if participant is None:
            return

        self.lower_third_display.show_participant(participant)
        self._schedule_auto_hide()

    def hide_lower_third(self) -> None:
        self._auto_hide_timer.stop()
        self.lower_third_display.hide_lower_third()

    def _schedule_auto_hide(self) -> None:
        self._auto_hide_timer.stop()
        if self.store.display_duration_seconds > 0:
            self._auto_hide_timer.start(self.store.display_duration_seconds * 1000)

    def _load_display_duration(self) -> int:
        return int(
            self._settings().value(
                "display_duration_seconds",
                self.store.display_duration_seconds,
            )
        )

    def _save_display_duration(self, seconds: int) -> None:
        self._settings().setValue("display_duration_seconds", seconds)

    def apply_display_duration(self, seconds: int) -> None:
        seconds = max(0, int(seconds))
        self.store.display_duration_seconds = seconds
        self.display_duration_spin.blockSignals(True)
        self.display_duration_spin.setValue(seconds)
        self.display_duration_spin.blockSignals(False)

    def _on_display_duration_changed(self, seconds: int) -> None:
        self.apply_display_duration(seconds)
        self._save_display_duration(seconds)
        if self.lower_third_display.has_active_participant():
            self._schedule_auto_hide()

    def _load_preview_background(self) -> str:
        return self._settings().value(
            "preview_background",
            self.store.preview_background,
            type=str,
        )

    def _save_preview_background(self, color: str) -> None:
        self._settings().setValue("preview_background", color)

    def apply_preview_background(self, color: str) -> None:
        parsed = QColor(color)
        if not parsed.isValid():
            parsed = QColor(DataStore.DEFAULT_PREVIEW_BACKGROUND)

        color = parsed.name()
        self.store.preview_background = color
        self.lower_third_display.set_background_color(color)
        self.preview_color_swatch.setStyleSheet(
            f"background-color: {color}; border: 1px solid #888;"
        )

    def set_preview_background(self, color: str) -> None:
        self.apply_preview_background(color)
        self._save_preview_background(color)

    def choose_preview_background(self) -> None:
        current = QColor(self.store.preview_background)
        chosen = QColorDialog.getColor(current, self, "Choose Chroma Background Color")
        if not chosen.isValid():
            return
        self.set_preview_background(chosen.name())

    def _load_lower_third_style_settings(self) -> tuple[str, str]:
        style = self._settings().value(
            "lower_third_style",
            DataStore.LOWER_THIRD_STYLE_DEFAULT,
            type=str,
        )
        background = self._settings().value("lower_third_background", "", type=str)
        return style, background

    def _save_lower_third_style_settings(self) -> None:
        self._settings().setValue("lower_third_style", self.store.lower_third_style)
        self._settings().setValue("lower_third_background", self.store.lower_third_background)

    def apply_lower_third_style(self) -> None:
        style = self.store.lower_third_style
        background_path = self.store.resolve_lower_third_background_path()

        if style == DataStore.LOWER_THIRD_STYLE_CUSTOM and background_path is None:
            style = DataStore.LOWER_THIRD_STYLE_DEFAULT
            self.store.lower_third_style = style

        self.lower_third_display.set_lower_third_style(style, background_path)

        combo_index = self.lower_third_style_combo.findData(style)
        self.lower_third_style_combo.blockSignals(True)
        self.lower_third_style_combo.setCurrentIndex(max(0, combo_index))
        self.lower_third_style_combo.blockSignals(False)

        using_custom = style == DataStore.LOWER_THIRD_STYLE_CUSTOM
        self.import_lower_third_button.setEnabled(using_custom)

        if using_custom and background_path is not None:
            self.lower_third_style_label.setText(str(background_path))
        elif using_custom:
            self.lower_third_style_label.setText("No background imported")
        else:
            self.lower_third_style_label.setText("Using built-in default lower third")

        self._update_default_appearance_enabled()

    def _update_default_appearance_enabled(self) -> None:
        enabled = self.store.lower_third_style == DataStore.LOWER_THIRD_STYLE_DEFAULT
        for widget in self._default_appearance_widgets:
            widget.setEnabled(enabled)

    def _set_color_swatch(self, swatch: QLabel, color: str) -> None:
        parsed = QColor(color)
        if not parsed.isValid():
            parsed = QColor("#000000")
        swatch.setStyleSheet(
            f"background-color: {parsed.name()}; border: 1px solid #888;"
        )

    def _load_default_appearance_settings(self) -> tuple[str, str]:
        bar_color = self._settings().value(
            "lower_third_bar_color",
            self.store.lower_third_bar_color,
            type=str,
        )
        accent_color = self._settings().value(
            "lower_third_accent_color",
            self.store.lower_third_accent_color,
            type=str,
        )
        return bar_color, accent_color

    def _save_default_appearance_settings(self) -> None:
        self._settings().setValue("lower_third_bar_color", self.store.lower_third_bar_color)
        self._settings().setValue("lower_third_accent_color", self.store.lower_third_accent_color)

    def apply_default_lower_third_appearance(
        self,
        appearance: tuple[str, str] | None = None,
    ) -> None:
        if appearance is None:
            bar_color = self.store.lower_third_bar_color
            accent_color = self.store.lower_third_accent_color
        else:
            bar_color, accent_color = appearance
            self.store.lower_third_bar_color = bar_color
            self.store.lower_third_accent_color = accent_color

        parsed_bar = QColor(bar_color)
        if not parsed_bar.isValid():
            parsed_bar = QColor(DataStore.DEFAULT_LOWER_THIRD_BAR_COLOR)
            bar_color = parsed_bar.name()
            self.store.lower_third_bar_color = bar_color

        parsed_accent = QColor(accent_color)
        if not parsed_accent.isValid():
            parsed_accent = QColor(DataStore.DEFAULT_LOWER_THIRD_ACCENT_COLOR)
            accent_color = parsed_accent.name()
            self.store.lower_third_accent_color = accent_color

        self._set_color_swatch(self.bar_color_swatch, bar_color)
        self._set_color_swatch(self.accent_color_swatch, accent_color)

        self.lower_third_display.set_default_lower_third_appearance(
            bar_color,
            accent_color,
        )
        self.lower_third_display.update()

    def choose_lower_third_bar_color(self) -> None:
        current = QColor(self.store.lower_third_bar_color)
        chosen = QColorDialog.getColor(current, self, "Choose Bar Background Color")
        if not chosen.isValid():
            return
        self.store.lower_third_bar_color = chosen.name()
        self.apply_default_lower_third_appearance()
        self._save_default_appearance_settings()

    def choose_lower_third_accent_color(self) -> None:
        current = QColor(self.store.lower_third_accent_color)
        chosen = QColorDialog.getColor(current, self, "Choose Accent Bar Color")
        if not chosen.isValid():
            return
        self.store.lower_third_accent_color = chosen.name()
        self.apply_default_lower_third_appearance()
        self._save_default_appearance_settings()

    def _on_lower_third_style_changed(self) -> None:
        style = self.lower_third_style_combo.currentData()
        if style == DataStore.LOWER_THIRD_STYLE_CUSTOM and not self.store.lower_third_background:
            self.import_lower_third_background()
            if not self.store.lower_third_background:
                self.apply_lower_third_style()
                return

        self.store.lower_third_style = style
        self.apply_lower_third_style()
        self._save_lower_third_style_settings()

    def import_lower_third_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Lower Third Background",
            self._default_json_directory(),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return

        if not Path(path).is_file():
            QMessageBox.warning(self, "Import Failed", "Could not find the selected image.")
            return

        self.store.lower_third_style = DataStore.LOWER_THIRD_STYLE_CUSTOM
        self.store.lower_third_background = str(Path(path))
        self.apply_lower_third_style()
        self._save_lower_third_style_settings()
