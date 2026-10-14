"""Study Pack Editor - trình soạn thảo study pack (JSON), bản PyQt6.

Cài đặt:  pip install PyQt6
Chạy:     python autoedit_qt.py

Dùng PySide6 thay cho PyQt6: đổi dòng import (PyQt6 -> PySide6); phần còn lại
giữ nguyên vì chỉ dùng API chung của Qt6.
"""

import json
import os
import subprocess
import sys
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QKeySequence,
    QPalette,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Study Pack Editor"
DEFAULT_THEME_MODE = "light"  # "light" | "dark" | "system"
BUILD_CHUNK = 20  # số dòng dựng mỗi đợt khi nạp danh sách dài
TAB_KEYS = ("notes", "terms", "flashcards", "questions")

PALETTES = {
    "light": {
        "bg": "#fafafa",
        "fg": "#1c1c1c",
        "field": "#ffffff",
        "border": "#cfcfcf",
        "accent": "#005fb8",
        "accent_fg": "#ffffff",
    },
    "dark": {
        "bg": "#1c1c1c",
        "fg": "#fafafa",
        "field": "#2b2b2b",
        "border": "#4a4a4a",
        "accent": "#57c8ff",
        "accent_fg": "#000000",
    },
}


# ----------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------
def detect_system_theme():
  """Trả về 'dark' hoặc 'light' theo cài đặt của hệ điều hành."""
  try:  # Qt >= 6.5 tự biết màu hệ thống
    scheme = QGuiApplication.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
      return "dark"
    if scheme == Qt.ColorScheme.Light:
      return "light"
  except AttributeError:
    pass
  try:
    if sys.platform == "win32":
      import winreg

      key = winreg.OpenKey(
          winreg.HKEY_CURRENT_USER,
          r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
      )
      try:
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
      finally:
        winreg.CloseKey(key)
      return "light" if value else "dark"
    if sys.platform == "darwin":
      out = subprocess.run(
          ["defaults", "read", "-g", "AppleInterfaceStyle"],
          capture_output=True,
          text=True,
          timeout=2,
      )
      return "dark" if out.stdout.strip().lower() == "dark" else "light"
    out = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
        capture_output=True,
        text=True,
        timeout=2,
    )
    return "dark" if "dark" in out.stdout.lower() else "light"
  except Exception:
    return "light"


def build_palette(p):
  """Tạo QPalette (dùng với style Fusion) từ bảng màu."""
  bg, fg, field = QColor(p["bg"]), QColor(p["fg"]), QColor(p["field"])
  accent, accent_fg = QColor(p["accent"]), QColor(p["accent_fg"])
  button = bg.lighter(118) if bg.lightness() < 128 else bg.darker(104)
  muted = QColor(fg)
  muted.setAlpha(120)

  pal = QPalette()
  R = QPalette.ColorRole
  for role, color in (
      (R.Window, bg),
      (R.WindowText, fg),
      (R.Base, field),
      (R.AlternateBase, bg),
      (R.Text, fg),
      (R.Button, button),
      (R.ButtonText, fg),
      (R.ToolTipBase, field),
      (R.ToolTipText, fg),
      (R.Highlight, accent),
      (R.HighlightedText, accent_fg),
      (R.PlaceholderText, muted),
      (R.Link, accent),
  ):
    pal.setColor(role, color)
  for role in (R.WindowText, R.Text, R.ButtonText):
    pal.setColor(QPalette.ColorGroup.Disabled, role, muted)
  return pal


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def bold_label(text):
  label = QLabel(text)
  font = label.font()
  font.setBold(True)
  label.setFont(font)
  return label


def fixed_label(text, width):
  label = QLabel(text)
  label.setFixedWidth(width)
  return label


def make_form(parent=None):
  form = QFormLayout(parent) if parent is not None else QFormLayout()
  form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
  form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
  return form


def set_list_items(listw, labels):
  """Nạp lại QListWidget mà không phát tín hiệu chọn."""
  listw.blockSignals(True)
  listw.clear()
  if labels:
    listw.addItems(labels)
  listw.blockSignals(False)


def select_row_silently(listw, row):
  listw.blockSignals(True)
  listw.setCurrentRow(row)
  listw.blockSignals(False)
  listw.scrollToItem(listw.item(row))


class ScrollList(QScrollArea):
  """Khung cuộn dọc chứa danh sách hàng.

  Danh sách dài được dựng theo từng đợt (QTimer) và tắt vẽ lại trong lúc dựng
  nên giao diện không bị đứng.
  """

  def __init__(self):
    super().__init__()
    self.setWidgetResizable(True)
    self.inner = QWidget()
    self.vbox = QVBoxLayout(self.inner)
    self.vbox.setContentsMargins(4, 4, 4, 4)
    self.vbox.addStretch(1)  # luôn nằm cuối, đẩy các hàng lên trên
    self.setWidget(self.inner)

    self._items = []
    self._pos = 0
    self._build_row = None
    self._timer = QTimer(self)
    self._timer.setSingleShot(True)
    self._timer.setInterval(1)
    self._timer.timeout.connect(self._build_step)

  # --- Widget ---
  def add_widget(self, widget):
    self.vbox.insertWidget(self.vbox.count() - 1, widget)

  def remove_widget(self, widget):
    self.vbox.removeWidget(widget)
    widget.setParent(None)
    widget.deleteLater()

  def scroll_top(self):
    self.verticalScrollBar().setValue(0)

  def scroll_to_end(self):
    bar = self.verticalScrollBar()
    QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

  def freeze(self):
    self.setUpdatesEnabled(False)

  def thaw(self):
    self.setUpdatesEnabled(True)

  # --- Nạp danh sách theo đợt ---
  def clear(self):
    self._timer.stop()
    self._items = []
    self._pos = 0
    while self.vbox.count() > 1:
      item = self.vbox.takeAt(0)
      widget = item.widget()
      if widget is not None:
        widget.setParent(None)
        widget.deleteLater()

  def populate(self, items, build_row):
    """Dựng danh sách; đợt đầu chạy ngay, phần còn lại dựng nền."""
    self.clear()
    self._items = list(items)
    self._build_row = build_row
    self.scroll_top()
    self._build_step()

  def _build_step(self):
    self.freeze()
    try:
      self._build_range(min(self._pos + BUILD_CHUNK, len(self._items)))
    finally:
      self.thaw()
    if self._pos < len(self._items):
      self._timer.start()

  def _build_range(self, end):
    while self._pos < end:
      item = self._items[self._pos]
      self._pos += 1
      self.add_widget(self._build_row(item))

  def flush(self):
    """Dựng nốt các dòng còn lại (gọi trước khi đọc dữ liệu từ form)."""
    self._timer.stop()
    if self._pos < len(self._items):
      self.freeze()
      try:
        self._build_range(len(self._items))
      finally:
        self.thaw()

  def append(self, item):
    self.flush()
    self._items.append(item)
    self._build_range(len(self._items))
    self.scroll_to_end()


class StudyPackEditor(QMainWindow):

  def __init__(self):
    super().__init__()
    self.set_initial_geometry()

    self.data = self.empty_pack()
    self.current_path = None
    self.current_topic_index = None
    self.current_question_index = None
    self.mode = "GUI"

    self.theme_mode = DEFAULT_THEME_MODE
    self._effective_theme = None
    self._last_theme_check = 0.0

    # Tab nào đang hiển thị đúng dữ liệu của chủ đề hiện tại (nạp lười)
    self._tab_loaded = {key: False for key in TAB_KEYS}
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []

    self.create_widgets()
    self.apply_theme()
    self.hook_theme_signals()
    self.update_title()

  @staticmethod
  def empty_pack():
    return {
        "format": "studypack",
        "version": 1,
        "title": "",
        "subject": "",
        "level": "",
        "language": "en",
        "topics": [],
    }

  def set_initial_geometry(self):
    avail = QGuiApplication.primaryScreen().availableGeometry()
    self.resize(min(1300, avail.width() - 80), min(850, avail.height() - 120))

  # ------------------------------------------------------------------
  # Theme
  # ------------------------------------------------------------------
  def apply_theme(self):
    if self.theme_mode == "system":
      effective = detect_system_theme()
    else:
      effective = self.theme_mode
    if effective == self._effective_theme:
      return
    self._effective_theme = effective
    QApplication.setPalette(build_palette(PALETTES[effective]))

  def change_theme(self):
    for value, button in self.theme_buttons.items():
      if button.isChecked():
        self.theme_mode = value
    self.apply_theme()

  def hook_theme_signals(self):
    """Theo dõi thay đổi theme của hệ điều hành."""
    app = QApplication.instance()
    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
      hints.colorSchemeChanged.connect(lambda *_: self.on_system_theme_hint())
    app.applicationStateChanged.connect(self.on_app_state_changed)

  def on_system_theme_hint(self):
    if self.theme_mode == "system":
      self.apply_theme()

  def on_app_state_changed(self, state):
    if state != Qt.ApplicationState.ApplicationActive:
      return
    if self.theme_mode != "system":
      return
    now = time.monotonic()
    if now - self._last_theme_check < 1.0:
      return
    self._last_theme_check = now
    self.apply_theme()

  # ------------------------------------------------------------------
  # Status / title
  # ------------------------------------------------------------------
  def set_status(self, message, timeout=4000):
    self.statusBar().showMessage(message, timeout)

  def update_title(self):
    name = os.path.basename(self.current_path) if self.current_path else None
    self.setWindowTitle(f"{name} - {APP_NAME}" if name else APP_NAME)

  # ------------------------------------------------------------------
  # Widgets
  # ------------------------------------------------------------------
  def add_menu_action(self, menu, text, slot, shortcut=None):
    action = QAction(text, self)
    if shortcut:
      action.setShortcut(QKeySequence(shortcut))
    action.triggered.connect(lambda _checked=False: slot())
    menu.addAction(action)

  def create_widgets(self):
    file_menu = self.menuBar().addMenu("&File")
    self.add_menu_action(file_menu, "New Study Pack", self.new_file, "Ctrl+N")
    self.add_menu_action(file_menu, "Open JSON...", self.open_file, "Ctrl+O")
    self.add_menu_action(file_menu, "Save JSON", self.save_file, "Ctrl+S")
    self.add_menu_action(
        file_menu, "Save JSON As...", self.save_file_as, "Ctrl+Shift+S"
    )
    file_menu.addSeparator()
    self.add_menu_action(file_menu, "Exit", self.close)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    self.setCentralWidget(splitter)

    # --- Cột trái: metadata và danh sách topic ---
    left = QWidget()
    left_v = QVBoxLayout(left)
    left_v.setContentsMargins(5, 5, 5, 5)

    meta_box = QGroupBox("General Information")
    meta_form = make_form(meta_box)
    self.meta_entries = {}
    for label, key in (
        ("Title:", "title"),
        ("Subject:", "subject"),
        ("Level:", "level"),
        ("Language:", "language"),
    ):
      ent = QLineEdit()
      ent.editingFinished.connect(
          lambda k=key, e=ent: self.update_meta(k, e)
      )
      meta_form.addRow(label, ent)
      self.meta_entries[key] = ent
    left_v.addWidget(meta_box)

    topic_box = QGroupBox("Topics")
    topic_v = QVBoxLayout(topic_box)
    self.topic_list = QListWidget()
    self.topic_list.currentRowChanged.connect(self.on_select_topic)
    topic_v.addWidget(self.topic_list, 1)
    btn_row = QHBoxLayout()
    add_btn = QPushButton("Add Topic")
    add_btn.clicked.connect(self.add_topic)
    del_btn = QPushButton("Delete Topic")
    del_btn.clicked.connect(self.delete_topic)
    btn_row.addWidget(add_btn)
    btn_row.addWidget(del_btn)
    topic_v.addLayout(btn_row)
    left_v.addWidget(topic_box, 1)

    # --- Cột phải: Editor và Settings ---
    self.main_tabs = QTabWidget()
    self.tab_editor = QWidget()
    self.tab_settings = QWidget()
    self.main_tabs.addTab(self.tab_editor, "Workspace")
    self.main_tabs.addTab(self.tab_settings, "Settings")

    splitter.addWidget(left)
    splitter.addWidget(self.main_tabs)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 4)
    splitter.setSizes([260, 1040])

    self.init_editor_workspace()
    self.init_settings_tab()

  def init_editor_workspace(self):
    root = QVBoxLayout(self.tab_editor)

    mode_row = QHBoxLayout()
    mode_row.addWidget(bold_label("Mode:"))
    mode_holder = QWidget()  # cùng parent => hai radio tự loại trừ nhau
    mode_h = QHBoxLayout(mode_holder)
    mode_h.setContentsMargins(0, 0, 0, 0)
    self.mode_gui_rb = QRadioButton("GUI Form")
    self.mode_text_rb = QRadioButton("Plain Text (JSON)")
    self.mode_gui_rb.setChecked(True)
    self.mode_gui_rb.clicked.connect(self.switch_mode)
    self.mode_text_rb.clicked.connect(self.switch_mode)
    mode_h.addWidget(self.mode_gui_rb)
    mode_h.addWidget(self.mode_text_rb)
    mode_row.addWidget(mode_holder)
    mode_row.addStretch(1)
    root.addLayout(mode_row)

    self.stack = QStackedWidget()
    root.addWidget(self.stack, 1)

    # --- View 1: Plain text ---
    self.text_page = QWidget()
    text_v = QVBoxLayout(self.text_page)
    text_v.setContentsMargins(0, 0, 0, 0)
    self.json_text = QPlainTextEdit()
    self.json_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    mono.setPointSize(10)
    self.json_text.setFont(mono)
    text_v.addWidget(self.json_text, 1)
    apply_row = QHBoxLayout()
    apply_row.addStretch(1)
    apply_btn = QPushButton("Apply Changes")
    apply_btn.clicked.connect(self.apply_plain_text)
    apply_row.addWidget(apply_btn)
    text_v.addLayout(apply_row)
    self.stack.addWidget(self.text_page)

    # --- View 2: Form ---
    self.gui_page = QWidget()
    gui_v = QVBoxLayout(self.gui_page)
    gui_v.setContentsMargins(0, 0, 0, 0)

    info = QGridLayout()
    self.t_id_ent = QLineEdit()
    self.t_id_ent.setFixedWidth(100)
    self.t_title_ent = QLineEdit()
    self.t_summary_ent = QLineEdit()
    info.addWidget(QLabel("ID:"), 0, 0)
    info.addWidget(self.t_id_ent, 0, 1)
    info.addWidget(QLabel("Title:"), 0, 2)
    info.addWidget(self.t_title_ent, 0, 3)
    info.addWidget(QLabel("Summary:"), 1, 0)
    info.addWidget(self.t_summary_ent, 1, 1, 1, 3)
    info.setColumnStretch(3, 1)
    for field, ent in (
        ("id", self.t_id_ent),
        ("title", self.t_title_ent),
        ("summary", self.t_summary_ent),
    ):
      ent.editingFinished.connect(
          lambda f=field, e=ent: self.update_current_topic_field(f, e)
      )
    gui_v.addLayout(info)

    self.topic_tabs = QTabWidget()
    self.tab_notes = QWidget()
    self.tab_terms = QWidget()
    self.tab_flashcards = QWidget()
    self.tab_questions = QWidget()
    self.topic_tabs.addTab(self.tab_notes, "Notes")
    self.topic_tabs.addTab(self.tab_terms, "Key Terms")
    self.topic_tabs.addTab(self.tab_flashcards, "Flashcards")
    self.topic_tabs.addTab(self.tab_questions, "Questions")
    gui_v.addWidget(self.topic_tabs, 1)
    self.stack.addWidget(self.gui_page)

    self.init_notes_gui()
    self.init_terms_gui()
    self.init_flashcards_gui()
    self.init_questions_gui()

    # Chỉ nạp dữ liệu của tab đang xem; tab khác nạp khi được mở.
    self.topic_tabs.currentChanged.connect(lambda _i: self.load_visible_tab())
    self.stack.setCurrentWidget(self.gui_page)

  def init_settings_tab(self):
    outer = QVBoxLayout(self.tab_settings)
    box = QGroupBox("Appearance")
    box_v = QVBoxLayout(box)
    box_v.addWidget(QLabel("Theme Mode:"))
    self.theme_buttons = {}
    for text, value in (
        ("Light", "light"),
        ("Dark", "dark"),
        ("System (Auto)", "system"),
    ):
      rb = QRadioButton(text)
      rb.setChecked(value == self.theme_mode)
      rb.clicked.connect(self.change_theme)
      box_v.addWidget(rb)
      self.theme_buttons[value] = rb
    box_v.addStretch(1)
    outer.addWidget(box, 1)

  # ------------------------------------------------------------------
  # Mode, commit, file operations
  # ------------------------------------------------------------------
  def render_json_text(self):
    self.json_text.setPlainText(
        json.dumps(self.data, ensure_ascii=False, indent=2)
    )
    self.json_text.document().setModified(False)

  def switch_mode(self):
    new_mode = "Text" if self.mode_text_rb.isChecked() else "GUI"
    if new_mode == "Text":
      if self.mode == "GUI":
        self.commit_meta()
        self.commit_current_topic()
      self.mode = new_mode
      self.stack.setCurrentWidget(self.text_page)
      self.render_json_text()
    else:
      self.mode = new_mode
      self.stack.setCurrentWidget(self.gui_page)
      self.load_topic_gui_data()

  def parse_pack_text(self, raw):
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError as e:
      QMessageBox.critical(self, "JSON Error", f"Invalid syntax: {e}")
      return None
    if not isinstance(parsed, dict):
      QMessageBox.critical(
          self, "JSON Error", "A study pack must be a JSON object."
      )
      return None
    parsed.setdefault("topics", [])
    return parsed

  def apply_plain_text(self):
    parsed = self.parse_pack_text(self.json_text.toPlainText())
    if parsed is None:
      return
    self.data = parsed
    self.refresh_ui()
    self.set_status("Changes applied.")

  def commit_pending(self):
    """Ghi mọi thay đổi chưa lưu trên giao diện về self.data.

    Trả về False nếu JSON ở chế độ Text không hợp lệ.
    """
    if self.mode == "Text":
      if self.json_text.document().isModified():
        parsed = self.parse_pack_text(self.json_text.toPlainText())
        if parsed is None:
          return False
        self.data = parsed
        self.refresh_ui()
      return True
    self.commit_meta()
    self.commit_current_topic()
    return True

  def commit_meta(self):
    for key, ent in self.meta_entries.items():
      value = ent.text()
      if value != str(self.data.get(key, "")):
        self.data[key] = value

  def commit_current_topic(self):
    """Ghi form của chủ đề đang mở về self.data (chỉ ở chế độ GUI)."""
    idx = self.current_topic_index
    topics = self.data.get("topics", [])
    if idx is None or self.mode != "GUI" or idx >= len(topics):
      return
    t = topics[idx]
    label_changed = False
    for field, ent in (
        ("id", self.t_id_ent),
        ("title", self.t_title_ent),
        ("summary", self.t_summary_ent),
    ):
      value = ent.text()
      if t.get(field, "") != value:
        t[field] = value
        label_changed = label_changed or field in ("id", "title")
    if label_changed:
      self.refresh_topic_list_item()

    if self._tab_loaded["notes"]:
      t["notes"] = self.collect_notes()
    if self._tab_loaded["terms"]:
      t["key_terms"] = self.collect_terms()
    if self._tab_loaded["flashcards"]:
      t["flashcards"] = self.collect_flashcards()
    if self._tab_loaded["questions"]:
      self.save_current_question_form(silent=True)

  def new_file(self):
    answer = QMessageBox.question(
        self,
        "Confirm",
        "Discard unsaved changes?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if answer == QMessageBox.StandardButton.Yes:
      self.data = self.empty_pack()
      self.current_path = None
      self.refresh_ui()
      self.update_title()

  def open_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Open JSON", "", "JSON files (*.json);;All files (*)"
    )
    if not file_path:
      return
    try:
      with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
      if not isinstance(data, dict):
        raise ValueError("A study pack must be a JSON object.")
    except Exception as e:
      QMessageBox.critical(self, "Error", f"Failed to read file:\n{e}")
      return
    data.setdefault("topics", [])
    self.data = data
    self.current_path = file_path
    self.refresh_ui()
    self.update_title()
    self.set_status(f"File loaded: {os.path.basename(file_path)}")

  def save_file(self):
    if not self.commit_pending():
      return
    if self.current_path:
      self.write_file(self.current_path)
    else:
      self.ask_save_path()

  def save_file_as(self):
    if self.commit_pending():
      self.ask_save_path()

  def ask_save_path(self):
    file_path, _ = QFileDialog.getSaveFileName(
        self, "Save JSON", "", "JSON files (*.json);;All files (*)"
    )
    if not file_path:
      return
    if not os.path.splitext(file_path)[1]:
      file_path += ".json"
    self.write_file(file_path)

  def write_file(self, file_path):
    tmp_path = file_path + ".tmp"
    try:
      with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(self.data, f, ensure_ascii=False, indent=2)
      os.replace(tmp_path, file_path)  # ghi nguyên tử, tránh hỏng file
    except Exception as e:
      QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
      return
    self.current_path = file_path
    self.update_title()
    self.set_status(f"File saved: {os.path.basename(file_path)}")

  # ------------------------------------------------------------------
  # Metadata và danh sách topic
  # ------------------------------------------------------------------
  def update_meta(self, key, entry):
    value = entry.text()
    if value != str(self.data.get(key, "")):
      self.data[key] = value

  @staticmethod
  def topic_label(t):
    return f"{t.get('id', '')}: {t.get('title', 'Untitled')}"

  def refresh_topic_list(self):
    set_list_items(
        self.topic_list,
        [self.topic_label(t) for t in self.data.get("topics", [])],
    )

  def refresh_topic_list_item(self):
    idx = self.current_topic_index
    if idx is None:
      return
    item = self.topic_list.item(idx)
    if item is not None:
      item.setText(self.topic_label(self.data["topics"][idx]))

  def invalidate_tabs(self):
    for key in self._tab_loaded:
      self._tab_loaded[key] = False
    self.current_question_index = None

  def reset_topic_view(self):
    """Xóa trạng thái chủ đề đang mở (khi đổi dữ liệu hoặc xóa topic)."""
    self.current_topic_index = None
    self.invalidate_tabs()
    for ent in (self.t_id_ent, self.t_title_ent, self.t_summary_ent):
      ent.clear()
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []
    self.notes_view.clear()
    self.terms_view.clear()
    self.fc_view.clear()
    set_list_items(self.q_list, [])
    self.q_detail.clear()

  def refresh_ui(self):
    self.reset_topic_view()
    for key, ent in self.meta_entries.items():
      ent.setText(str(self.data.get(key, "")))
    self.refresh_topic_list()
    if self.mode == "Text":
      self.render_json_text()

  def add_topic(self):
    self.commit_current_topic()
    topics = self.data.setdefault("topics", [])
    new_t = {
        "id": f"t{len(topics) + 1}",
        "title": "New Topic",
        "summary": "",
        "notes": [],
        "key_terms": [],
        "flashcards": [],
        "questions": [],
    }
    topics.append(new_t)
    idx = len(topics) - 1
    self.topic_list.blockSignals(True)
    self.topic_list.addItem(self.topic_label(new_t))
    self.topic_list.blockSignals(False)
    select_row_silently(self.topic_list, idx)
    self.on_select_topic()
    if self.mode == "Text":
      self.render_json_text()

  def delete_topic(self):
    row = self.topic_list.currentRow()
    if row < 0:
      return
    del self.data["topics"][row]
    self.reset_topic_view()
    self.refresh_topic_list()
    if self.mode == "Text":
      self.render_json_text()

  def on_select_topic(self, _row=None):
    idx = self.topic_list.currentRow()
    if idx < 0 or idx == self.current_topic_index:
      return
    self.commit_current_topic()  # lưu form của topic trước khi chuyển
    self.current_topic_index = idx
    self.invalidate_tabs()
    if self.mode == "GUI":
      self.load_topic_gui_data()

  def update_current_topic_field(self, field, entry):
    idx = self.current_topic_index
    if idx is None or idx >= len(self.data.get("topics", [])):
      return
    t = self.data["topics"][idx]
    value = entry.text()
    if t.get(field, "") == value:
      return
    t[field] = value
    if field in ("id", "title"):
      self.refresh_topic_list_item()

  def load_topic_gui_data(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    self.t_id_ent.setText(str(t.get("id", "")))
    self.t_title_ent.setText(str(t.get("title", "")))
    self.t_summary_ent.setText(str(t.get("summary", "")))
    self.load_visible_tab()

  def load_visible_tab(self):
    """Nạp dữ liệu cho tab đang xem nếu chưa nạp."""
    if self.current_topic_index is None or self.mode != "GUI":
      return
    key = TAB_KEYS[self.topic_tabs.currentIndex()]
    if self._tab_loaded[key]:
      return
    t = self.data["topics"][self.current_topic_index]
    if key == "notes":
      self.load_notes_ui(t.get("notes", []))
    elif key == "terms":
      self.load_terms_ui(t.get("key_terms", []))
    elif key == "flashcards":
      self.load_flashcards_ui(t.get("flashcards", []))
    else:
      self.load_questions_list()
    self._tab_loaded[key] = True

  # ------------------------------------------------------------------
  # Thanh điều khiển dùng chung cho các tab Notes/Terms/Flashcards
  # ------------------------------------------------------------------
  def make_list_tab(self, tab, add_text, add_slot, save_text, save_slot):
    v = QVBoxLayout(tab)
    top = QHBoxLayout()
    add_btn = QPushButton(add_text)
    add_btn.clicked.connect(add_slot)
    save_btn = QPushButton(save_text)
    save_btn.clicked.connect(save_slot)
    top.addWidget(add_btn)
    top.addStretch(1)
    top.addWidget(save_btn)
    v.addLayout(top)
    view = ScrollList()
    v.addWidget(view, 1)
    return view

  # ------------------------------------------------------------------
  # 1. Notes
  # ------------------------------------------------------------------
  def init_notes_gui(self):
    self.notes_view = self.make_list_tab(
        self.tab_notes,
        "+ Add Section",
        self.add_note_section,
        "Save Notes",
        self.save_notes_form,
    )

  def load_notes_ui(self, notes_list):
    self.note_widgets = []
    self.notes_view.populate(notes_list, self.build_note_section)

  def build_note_section(self, sec):
    group = QGroupBox(f"Section {len(self.note_widgets) + 1}")
    v = QVBoxLayout(group)

    head = QHBoxLayout()
    head.addWidget(QLabel("Heading:"))
    h_ent = QLineEdit(str(sec.get("heading", "")))
    head.addWidget(h_ent, 1)
    del_btn = QPushButton("Delete")
    del_btn.clicked.connect(
        lambda _c=False, g=group: self.remove_note_section(g)
    )
    head.addWidget(del_btn)
    v.addLayout(head)

    v.addWidget(QLabel("Points:"))
    p_txt = QPlainTextEdit()
    p_txt.setTabChangesFocus(True)
    p_txt.setPlainText("\n".join(str(p) for p in sec.get("points", [])))
    p_txt.setFixedHeight(p_txt.fontMetrics().lineSpacing() * 4 + 16)
    v.addWidget(p_txt)

    self.note_widgets.append((h_ent, p_txt, group))
    return group

  def add_note_section(self):
    if self.current_topic_index is None:
      return
    self.notes_view.append(
        {"heading": "New Section", "points": ["Point about **term**."]}
    )

  def remove_note_section(self, group):
    self.note_widgets = [w for w in self.note_widgets if w[2] is not group]
    self.notes_view.remove_widget(group)

  def collect_notes(self):
    self.notes_view.flush()
    notes = []
    for h_ent, p_txt, _ in self.note_widgets:
      points = [
          pt.strip() for pt in p_txt.toPlainText().splitlines() if pt.strip()
      ]
      notes.append({"heading": h_ent.text(), "points": points})
    return notes

  def save_notes_form(self):
    if self.current_topic_index is None:
      return
    self.data["topics"][self.current_topic_index]["notes"] = self.collect_notes()
    self.set_status("Notes updated.")

  # ------------------------------------------------------------------
  # 2. Key terms
  # ------------------------------------------------------------------
  def init_terms_gui(self):
    self.terms_view = self.make_list_tab(
        self.tab_terms,
        "+ Add Term",
        self.add_term_row,
        "Save Terms",
        self.save_terms_form,
    )

  def load_terms_ui(self, terms_list):
    self.term_widgets = []
    self.terms_view.populate(terms_list, self.build_term_row)

  def build_term_row(self, item):
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(2, 2, 2, 2)
    h.addWidget(fixed_label(f"Term {len(self.term_widgets) + 1}:", 60))
    t_ent = QLineEdit(str(item.get("term", "")))
    t_ent.setMinimumWidth(170)
    h.addWidget(t_ent, 1)
    h.addWidget(fixed_label("Def:", 32))
    d_ent = QLineEdit(str(item.get("definition", "")))
    h.addWidget(d_ent, 3)
    del_btn = QPushButton("X")
    del_btn.setFixedWidth(34)
    del_btn.clicked.connect(lambda _c=False, r=row: self.remove_term_row(r))
    h.addWidget(del_btn)
    self.term_widgets.append((t_ent, d_ent, row))
    return row

  def add_term_row(self):
    if self.current_topic_index is None:
      return
    self.terms_view.append({"term": "New Term", "definition": "Definition here."})

  def remove_term_row(self, row):
    self.term_widgets = [w for w in self.term_widgets if w[2] is not row]
    self.terms_view.remove_widget(row)

  def collect_terms(self):
    self.terms_view.flush()
    return [
        {"term": t_ent.text(), "definition": d_ent.text()}
        for t_ent, d_ent, _ in self.term_widgets
    ]

  def save_terms_form(self):
    if self.current_topic_index is None:
      return
    self.data["topics"][self.current_topic_index]["key_terms"] = (
        self.collect_terms()
    )
    self.set_status("Key terms updated.")

  # ------------------------------------------------------------------
  # 3. Flashcards
  # ------------------------------------------------------------------
  def init_flashcards_gui(self):
    self.fc_view = self.make_list_tab(
        self.tab_flashcards,
        "+ Add Flashcard",
        self.add_fc_row,
        "Save Flashcards",
        self.save_fc_form,
    )

  def load_flashcards_ui(self, fc_list):
    self.fc_widgets = []
    self.fc_view.populate(fc_list, self.build_fc_row)

  def build_fc_row(self, fc):
    group = QGroupBox(f"Flashcard {len(self.fc_widgets) + 1}")
    v = QVBoxLayout(group)
    form = make_form()
    f_ent = QLineEdit(str(fc.get("front", "")))
    b_ent = QLineEdit(str(fc.get("back", "")))
    form.addRow("Front:", f_ent)
    form.addRow("Back:", b_ent)
    v.addLayout(form)
    btn_row = QHBoxLayout()
    btn_row.addStretch(1)
    del_btn = QPushButton("Delete")
    del_btn.clicked.connect(lambda _c=False, g=group: self.remove_fc_row(g))
    btn_row.addWidget(del_btn)
    v.addLayout(btn_row)
    self.fc_widgets.append((f_ent, b_ent, group))
    return group

  def add_fc_row(self):
    if self.current_topic_index is None:
      return
    self.fc_view.append({"front": "Question?", "back": "Answer."})

  def remove_fc_row(self, group):
    self.fc_widgets = [w for w in self.fc_widgets if w[2] is not group]
    self.fc_view.remove_widget(group)

  def collect_flashcards(self):
    self.fc_view.flush()
    return [
        {"front": f_ent.text(), "back": b_ent.text()}
        for f_ent, b_ent, _ in self.fc_widgets
    ]

  def save_fc_form(self):
    if self.current_topic_index is None:
      return
    self.data["topics"][self.current_topic_index]["flashcards"] = (
        self.collect_flashcards()
    )
    self.set_status("Flashcards updated.")

  # ------------------------------------------------------------------
  # 4. Questions
  # ------------------------------------------------------------------
  def init_questions_gui(self):
    outer = QVBoxLayout(self.tab_questions)
    outer.setContentsMargins(2, 2, 2, 2)
    splitter = QSplitter(Qt.Orientation.Horizontal)
    outer.addWidget(splitter)

    left = QWidget()
    left_v = QVBoxLayout(left)
    left_v.addWidget(bold_label("Questions List"))
    self.q_list = QListWidget()
    self.q_list.currentRowChanged.connect(self.on_select_question_item)
    left_v.addWidget(self.q_list, 1)

    ctrl = QHBoxLayout()
    self.q_type_combo = QComboBox()
    self.q_type_combo.addItems(
        ["mcq", "truefalse", "short", "cloze", "match", "tfs"]
    )
    add_btn = QPushButton("+ Add")
    add_btn.clicked.connect(self.add_single_question)
    del_btn = QPushButton("Delete")
    del_btn.clicked.connect(self.delete_single_question)
    ctrl.addWidget(self.q_type_combo)
    ctrl.addWidget(add_btn)
    ctrl.addWidget(del_btn)
    left_v.addLayout(ctrl)

    right = QWidget()
    right_v = QVBoxLayout(right)
    self.q_detail = ScrollList()
    right_v.addWidget(self.q_detail, 1)
    save_row = QHBoxLayout()
    save_row.addStretch(1)
    save_btn = QPushButton("Save Question Changes")
    save_btn.clicked.connect(lambda _c=False: self.save_current_question_form())
    save_row.addWidget(save_btn)
    right_v.addLayout(save_row)

    splitter.addWidget(left)
    splitter.addWidget(right)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 3)
    splitter.setSizes([260, 780])

  @staticmethod
  def question_label(idx, q):
    prompt = str(q.get("prompt", ""))
    snippet = prompt[:35] + ("..." if len(prompt) > 35 else "")
    return f"Q{idx + 1} [{q.get('type', 'mcq')}]: {snippet}"

  def load_questions_list(self):
    self.current_question_index = None
    self.q_detail.clear()
    if self.current_topic_index is None:
      set_list_items(self.q_list, [])
      return
    questions = self.data["topics"][self.current_topic_index].get(
        "questions", []
    )
    set_list_items(
        self.q_list, [self.question_label(i, q) for i, q in enumerate(questions)]
    )

  def on_select_question_item(self, _row=None):
    idx = self.q_list.currentRow()
    if idx < 0 or idx == self.current_question_index:
      return
    if self.current_question_index is not None:
      self.save_current_question_form(silent=True)
    self.current_question_index = idx
    self.render_single_question_form()

  def render_single_question_form(self):
    self.q_detail.clear()
    if (
        self.current_topic_index is None
        or self.current_question_index is None
    ):
      return
    questions = self.data["topics"][self.current_topic_index].get(
        "questions", []
    )
    if self.current_question_index >= len(questions):
      return

    self.q_detail.scroll_top()
    self.q_detail.freeze()
    try:
      self.q_detail.add_widget(
          self.build_question_form(questions[self.current_question_index])
      )
    finally:
      self.q_detail.thaw()

  def build_question_form(self, q):
    q_type = q.get("type", "mcq")
    form_w = QWidget()
    v = QVBoxLayout(form_w)
    v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(
        bold_label(
            f"Editing Question {self.current_question_index + 1} "
            f"[{q_type.upper()}]"
        )
    )

    form = make_form()
    v.addLayout(form)
    self.det_prompt_ent = QLineEdit(str(q.get("prompt", "")))
    form.addRow("Prompt:", self.det_prompt_ent)

    self.det_spec = {"type": q_type}

    if q_type == "mcq":
      self.det_mcq_context = QLineEdit(str(q.get("context", "")))
      form.addRow("Context:", self.det_mcq_context)
      self.det_mcq_source = QLineEdit(str(q.get("source", "")))
      form.addRow("Source:", self.det_mcq_source)

      opts = q.get("options", ["", "", "", ""])
      self.det_spec["opt_ents"] = []
      for o_idx, opt_text in enumerate(opts):
        o_ent = QLineEdit(str(opt_text))
        form.addRow(f"Option {o_idx}:", o_ent)
        self.det_spec["opt_ents"].append(o_ent)

      self.det_ans_spin = QSpinBox()
      self.det_ans_spin.setRange(0, max(3, len(opts) - 1))
      try:
        self.det_ans_spin.setValue(int(q.get("answer", 0)))
      except (TypeError, ValueError):
        self.det_ans_spin.setValue(0)
      self.det_ans_spin.setMaximumWidth(90)
      form.addRow("Correct Index:", self.det_ans_spin)

    elif q_type == "truefalse":
      holder, self.det_tf_true = self.make_true_false(
          "True", "False", str(q.get("answer", True)) == "True"
      )
      form.addRow("Answer:", holder)

    elif q_type == "short":
      self.det_short_ent = QLineEdit(str(q.get("answer", "")))
      form.addRow("Model Answer:", self.det_short_ent)

    elif q_type == "cloze":
      ans_list = q.get("answers", [])
      self.det_cloze_ent = QLineEdit(
          ", ".join(str(a) for a in ans_list)
          if isinstance(ans_list, list)
          else str(ans_list)
      )
      form.addRow("Answers:", self.det_cloze_ent)

    elif q_type == "match":
      self.det_spec["pair_ents"] = []
      group = QGroupBox("Pairs (Left : Right)")
      group_v = QVBoxLayout(group)
      for p_obj in q.get("pairs", []):
        row = QHBoxLayout()
        l_ent = QLineEdit(str(p_obj.get("left", "")))
        l_ent.setMinimumWidth(160)
        r_ent = QLineEdit(str(p_obj.get("right", "")))
        row.addWidget(l_ent, 1)
        row.addWidget(QLabel("->"))
        row.addWidget(r_ent, 3)
        group_v.addLayout(row)
        self.det_spec["pair_ents"].append((l_ent, r_ent))
      v.addWidget(group)

    elif q_type == "tfs":
      self.det_quote_ent = QLineEdit(str(q.get("quote", "")))
      form.addRow("Quote:", self.det_quote_ent)
      self.det_tfs_source = QLineEdit(str(q.get("source", "")))
      form.addRow("Source:", self.det_tfs_source)

      self.det_spec["tfs_item_ents"] = []
      group = QGroupBox("Statements & Answers")
      group_v = QVBoxLayout(group)
      for itm in q.get("items", []):
        row = QHBoxLayout()
        txt_ent = QLineEdit(str(itm.get("text", "")))
        row.addWidget(txt_ent, 1)
        holder, t_rb = self.make_true_false(
            "T", "F", str(itm.get("answer", True)) == "True"
        )
        row.addWidget(holder)
        group_v.addLayout(row)
        self.det_spec["tfs_item_ents"].append((txt_ent, t_rb))
      v.addWidget(group)

    end_form = make_form()
    self.det_exp_ent = QLineEdit(str(q.get("explanation", "")))
    end_form.addRow("Explanation:", self.det_exp_ent)
    v.addLayout(end_form)
    return form_w

  @staticmethod
  def make_true_false(true_text, false_text, is_true):
    """Cặp radio True/False; trả về (widget chứa, radio 'True')."""
    holder = QWidget()  # parent riêng => mỗi cặp là một nhóm loại trừ
    h = QHBoxLayout(holder)
    h.setContentsMargins(0, 0, 0, 0)
    t_rb = QRadioButton(true_text)
    f_rb = QRadioButton(false_text)
    t_rb.setChecked(is_true)
    f_rb.setChecked(not is_true)
    h.addWidget(t_rb)
    h.addWidget(f_rb)
    h.addStretch(1)
    return holder, t_rb

  @staticmethod
  def set_or_remove(q, key, value):
    value = value.strip()
    if value:
      q[key] = value
    else:
      q.pop(key, None)

  def save_current_question_form(self, silent=False):
    if (
        self.current_topic_index is None
        or self.current_question_index is None
    ):
      return
    t = self.data["topics"][self.current_topic_index]
    questions = t.get("questions", [])
    if self.current_question_index >= len(questions):
      return

    q = questions[self.current_question_index]
    q_type = q.get("type", "mcq")

    q["prompt"] = self.det_prompt_ent.text()
    q["explanation"] = self.det_exp_ent.text()

    if q_type == "mcq":
      q["options"] = [ent.text() for ent in self.det_spec["opt_ents"]]
      q["answer"] = self.det_ans_spin.value()
      self.set_or_remove(q, "context", self.det_mcq_context.text())
      self.set_or_remove(q, "source", self.det_mcq_source.text())
    elif q_type == "truefalse":
      q["answer"] = self.det_tf_true.isChecked()
    elif q_type == "short":
      q["answer"] = self.det_short_ent.text()
    elif q_type == "cloze":
      ans_str = self.det_cloze_ent.text()
      q["answers"] = [a.strip() for a in ans_str.split(",") if a.strip()]
    elif q_type == "match":
      q["pairs"] = [
          {"left": l_ent.text(), "right": r_ent.text()}
          for l_ent, r_ent in self.det_spec["pair_ents"]
      ]
    elif q_type == "tfs":
      q["quote"] = self.det_quote_ent.text()
      self.set_or_remove(q, "source", self.det_tfs_source.text())
      q["items"] = [
          {"text": txt_ent.text(), "answer": t_rb.isChecked()}
          for txt_ent, t_rb in self.det_spec["tfs_item_ents"]
      ]

    idx = self.current_question_index
    item = self.q_list.item(idx)
    if item is not None:
      item.setText(self.question_label(idx, q))

    if not silent:
      self.set_status("Question updated.")

  def add_single_question(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    questions = t.setdefault("questions", [])

    q_type = self.q_type_combo.currentText()
    new_q = {
        "type": q_type,
        "prompt": "New question prompt?",
        "explanation": "Explanation.",
    }
    if q_type == "mcq":
      new_q["options"] = ["Opt A", "Opt B", "Opt C", "Opt D"]
      new_q["answer"] = 0
    elif q_type == "truefalse":
      new_q["answer"] = True
    elif q_type == "short":
      new_q["answer"] = "Model answer"
    elif q_type == "cloze":
      new_q["answers"] = ["answer1"]
    elif q_type == "match":
      new_q["pairs"] = [
          {"left": "L1", "right": "R1"},
          {"left": "L2", "right": "R2"},
          {"left": "L3", "right": "R3"},
          {"left": "L4", "right": "R4"},
      ]
    elif q_type == "tfs":
      new_q["quote"] = "Quote text."
      new_q["source"] = ""
      new_q["items"] = [
          {"text": "Statement 1", "answer": True},
          {"text": "Statement 2", "answer": False},
          {"text": "Statement 3", "answer": True},
          {"text": "Statement 4", "answer": False},
      ]

    # Lưu câu đang mở trước (qua on_select_question_item), chỉ thêm 1 dòng
    questions.append(new_q)
    idx = len(questions) - 1
    self.q_list.blockSignals(True)
    self.q_list.addItem(self.question_label(idx, new_q))
    self.q_list.blockSignals(False)
    select_row_silently(self.q_list, idx)
    self.on_select_question_item()

  def delete_single_question(self):
    row = self.q_list.currentRow()
    if row < 0 or self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    del t["questions"][row]
    self.load_questions_list()


def main():
  app = QApplication(sys.argv)
  app.setApplicationName(APP_NAME)
  app.setStyle("Fusion")  # style nhất quán, hỗ trợ đổi palette sáng/tối
  window = StudyPackEditor()
  window.show()
  sys.exit(app.exec())


if __name__ == "__main__":
  main()
