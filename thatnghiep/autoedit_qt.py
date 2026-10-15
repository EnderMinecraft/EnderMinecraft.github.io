"""Study Pack Editor - trình soạn thảo study pack (JSON), bản PyQt6.

Giao diện kiểu Windows 10/11 (Fluent): style Fusion + QSS + màu thanh tiêu đề.

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
from string import Template

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QKeySequence,
    QPalette,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Study Pack Editor"
DEFAULT_THEME_MODE = "light"  # "light" | "dark" | "system"
BUILD_CHUNK = 20  # số dòng dựng mỗi đợt khi nạp danh sách dài
TAB_KEYS = ("notes", "terms", "flashcards", "questions")
QUESTION_TYPES = ("mcq", "truefalse", "short", "cloze", "match", "tfs")
MAX_LABEL_CHARS = 80  # cắt nhãn dài trong danh sách

# Bảng màu theo Fluent / Windows 11. Dùng cho cả QPalette lẫn QSS.
PALETTES = {
    "light": {
        "bg": "#f3f3f3",
        "fg": "#1a1a1a",
        "fg2": "#5f5f5f",
        "fg3": "#a0a0a0",
        "field": "#ffffff",
        "field_hover": "#f9f9f9",
        "card": "#ffffff",
        "pane": "#f9f9f9",
        "border": "#e0e0e0",
        "border_b": "#8a8a8a",
        "btn": "#fdfdfd",
        "btn_hover": "#f6f6f6",
        "btn_press": "#ececec",
        "btn_dis": "#f5f5f5",
        "hover": "#eaeaea",
        "sel": "#e3e3e3",
        "accent": "#005fb8",
        "accent_hover": "#1a6fc0",
        "accent_press": "#3a82c8",
        "accent_fg": "#ffffff",
        "scroll": "#c2c2c2",
        "scroll_hover": "#8a8a8a",
        "warn_bg": "#fff4ce",
        "warn_border": "#e8c25a",
        "err_bg": "#fde7e9",
        "err_border": "#d13438",
    },
    "dark": {
        "bg": "#202020",
        "fg": "#ffffff",
        "fg2": "#c8c8c8",
        "fg3": "#707070",
        "field": "#2d2d2d",
        "field_hover": "#323232",
        "card": "#2b2b2b",
        "pane": "#252525",
        "border": "#3d3d3d",
        "border_b": "#8a8a8a",
        "btn": "#2f2f2f",
        "btn_hover": "#353535",
        "btn_press": "#282828",
        "btn_dis": "#2a2a2a",
        "hover": "#383838",
        "sel": "#3a3a3a",
        "accent": "#57c8ff",
        "accent_hover": "#6fd0ff",
        "accent_press": "#45b3e8",
        "accent_fg": "#000000",
        "scroll": "#5a5a5a",
        "scroll_hover": "#8a8a8a",
        "warn_bg": "#433519",
        "warn_border": "#9d5d00",
        "err_bg": "#442726",
        "err_border": "#d13438",
    },
}

# Dùng type selector (không dùng descendant selector) để việc dựng nhiều hàng
# widget không bị chậm vì QSS.
STYLE_TEMPLATE = Template(
    """
QMainWindow, QDialog, QMessageBox { background: $bg; }
QToolTip { background: $card; color: $fg; border: 1px solid $border; padding: 4px 6px; }
QStatusBar { background: $bg; color: $fg2; }
QStatusBar::item { border: none; }

QMenuBar { background: $bg; padding: 2px 4px; }
QMenuBar::item { background: transparent; padding: 5px 10px; border-radius: 4px; }
QMenuBar::item:selected { background: $hover; }
QMenu { background: $card; border: 1px solid $border; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 12px; margin: 1px 2px; border-radius: 4px; }
QMenu::item:selected { background: $hover; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }

QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 8px; }

QTabWidget::pane { border: 1px solid $border; border-radius: 8px; background: $pane; top: -1px; }
QTabBar::tab { background: transparent; color: $fg2; padding: 7px 16px; margin: 0 2px; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:hover { background: $hover; border-radius: 4px; }
QTabBar::tab:selected { color: $fg; border-bottom: 2px solid $accent; }

QGroupBox { background: $card; border: 1px solid $border; border-radius: 8px; margin-top: 22px; padding: 12px 10px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 2px; padding: 0 2px 4px 2px; color: $fg2; }

QPushButton { background: $btn; color: $fg; border: 1px solid $border; border-bottom-color: $border_b; border-radius: 4px; padding: 5px 14px; min-height: 18px; }
QPushButton:hover { background: $btn_hover; }
QPushButton:pressed { background: $btn_press; color: $fg2; }
QPushButton:focus { border-color: $accent; }
QPushButton:disabled { background: $btn_dis; color: $fg3; border-bottom-color: $border; }
QPushButton[primary="true"] { background: $accent; color: $accent_fg; border: 1px solid $accent; }
QPushButton[primary="true"]:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton[primary="true"]:pressed { background: $accent_press; border-color: $accent_press; color: $accent_fg; }
QPushButton[subtle="true"] { background: transparent; border: 1px solid transparent; padding: 0; min-height: 0; }
QPushButton[subtle="true"]:hover { background: $hover; }
QPushButton[subtle="true"]:pressed { background: $btn_press; }

QLineEdit, QPlainTextEdit, QComboBox { background: $field; color: $fg; border: 1px solid $border; border-bottom: 1px solid $border_b; border-radius: 4px; padding: 4px 8px; selection-background-color: $accent; selection-color: $accent_fg; }
QLineEdit:hover, QPlainTextEdit:hover, QComboBox:hover { background: $field_hover; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { background: $field; border-bottom: 2px solid $accent; }
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled { background: $btn_dis; color: $fg3; }
QComboBox QAbstractItemView { background: $card; border: 1px solid $border; selection-background-color: $sel; selection-color: $fg; outline: 0; padding: 4px; }

QListWidget { background: $card; border: 1px solid $border; border-radius: 6px; padding: 4px; outline: 0; }
QListWidget::item { padding: 6px 8px; margin: 1px 0; border-radius: 4px; }
QListWidget::item:hover { background: $hover; }
QListWidget::item:selected { background: $sel; color: $fg; border-left: 3px solid $accent; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: $scroll; min-height: 30px; border-radius: 3px; margin: 0 3px; }
QScrollBar::handle:vertical:hover { background: $scroll_hover; margin: 0 2px; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: $scroll; min-width: 30px; border-radius: 3px; margin: 3px 0; }
QScrollBar::handle:horizontal:hover { background: $scroll_hover; margin: 2px 0; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QLabel[banner="warn"] { background: $warn_bg; color: $fg; border: 1px solid $warn_border; border-radius: 6px; padding: 8px 10px; }
QLabel[banner="error"] { background: $err_bg; color: $fg; border: 1px solid $err_border; border-radius: 6px; padding: 8px 10px; }

QPushButton[badge="dirty"] { background: $warn_bg; color: $fg; border: 1px solid $warn_border; border-radius: 12px; padding: 3px 14px; min-height: 0; font-weight: 600; }
QPushButton[badge="dirty"]:hover { background: $warn_border; }
QPushButton[badge="clean"] { background: transparent; color: $fg2; border: 1px solid transparent; padding: 3px 14px; min-height: 0; }
"""
)


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
  """Tạo QPalette (cho style Fusion) từ bảng màu."""
  fg = QColor(p["fg"])
  muted = QColor(p["fg3"])
  pal = QPalette()
  R = QPalette.ColorRole
  for role, color in (
      (R.Window, QColor(p["bg"])),
      (R.WindowText, fg),
      (R.Base, QColor(p["field"])),
      (R.AlternateBase, QColor(p["pane"])),
      (R.Text, fg),
      (R.Button, QColor(p["btn"])),
      (R.ButtonText, fg),
      (R.ToolTipBase, QColor(p["card"])),
      (R.ToolTipText, fg),
      (R.Highlight, QColor(p["accent"])),
      (R.HighlightedText, QColor(p["accent_fg"])),
      (R.PlaceholderText, muted),
      (R.Link, QColor(p["accent"])),
  ):
    pal.setColor(role, color)
  for role in (R.WindowText, R.Text, R.ButtonText):
    pal.setColor(QPalette.ColorGroup.Disabled, role, muted)
  return pal


def colorref(hex_color):
  """'#rrggbb' -> COLORREF (0x00BBGGRR) của Windows."""
  c = QColor(hex_color)
  return c.red() | (c.green() << 8) | (c.blue() << 16)


def set_titlebar(hwnd, dark, caption_hex, text_hex):
  """Thanh tiêu đề tối/sáng và (Win11) cùng màu với nền cửa sổ."""
  if sys.platform != "win32":
    return
  try:
    import ctypes

    dwm = ctypes.windll.dwmapi

    def set_attr(attr, value):
      v = ctypes.c_int(value)
      return dwm.DwmSetWindowAttribute(
          ctypes.c_void_p(hwnd),
          ctypes.c_uint(attr),
          ctypes.byref(v),
          ctypes.c_uint(ctypes.sizeof(v)),
      )

    # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 20H1+, Win11);
    # 19 là mã cũ của một số bản Win10 đầu.
    if set_attr(20, int(dark)) != 0:
      set_attr(19, int(dark))
    if sys.getwindowsversion().build >= 22000:  # Windows 11
      set_attr(35, colorref(caption_hex))  # DWMWA_CAPTION_COLOR
      set_attr(36, colorref(text_hex))  # DWMWA_TEXT_COLOR
  except Exception:
    pass


_ICON_FAMILY = None


def icon_font_family():
  """Font icon của Windows (Win11: Segoe Fluent Icons, Win10: MDL2)."""
  global _ICON_FAMILY
  if _ICON_FAMILY is None:
    _ICON_FAMILY = ""
    if sys.platform == "win32":
      families = set(QFontDatabase.families())
      for fam in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if fam in families:
          _ICON_FAMILY = fam
          break
  return _ICON_FAMILY


def make_button(text, primary=False):
  btn = QPushButton(text)
  # Chỉ focus bằng phím Tab nên viền focus không dính lại sau khi click chuột.
  btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
  if primary:
    btn.setProperty("primary", True)
  return btn


def make_icon_button(glyph, fallback, tooltip):
  btn = QPushButton()
  fam = icon_font_family()
  if fam:
    btn.setText(glyph)
    font = QFont(fam)
    font.setPointSize(10)
    btn.setFont(font)
  else:
    btn.setText(fallback)
  btn.setToolTip(tooltip)
  btn.setFixedSize(32, 28)
  btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
  btn.setProperty("subtle", True)
  return btn


# ----------------------------------------------------------------------
# Dữ liệu: đọc an toàn file JSON sai cấu trúc
# ----------------------------------------------------------------------
def json_type_name(value):
  if value is None:
    return "null"
  if isinstance(value, bool):
    return "boolean"
  if isinstance(value, (int, float)):
    return "number"
  if isinstance(value, str):
    return "string"
  if isinstance(value, list):
    return "array"
  return "object"


def as_list(value):
  return value if isinstance(value, list) else []


def as_dict(value):
  return value if isinstance(value, dict) else {}


def clip(text, limit=MAX_LABEL_CHARS):
  text = str(text).replace("\n", " ").replace("\r", " ")
  return text if len(text) <= limit else text[: limit - 1] + "…"


def to_bool(value, default=True):
  """Đọc đáp án đúng/sai một cách dễ dãi (True, 1, 'true', ...)."""
  if isinstance(value, bool):
    return value
  if isinstance(value, (int, float)):
    return value != 0
  if isinstance(value, str):
    s = value.strip().lower()
    if s in ("true", "1", "yes", "t"):
      return True
    if s in ("false", "0", "no", "f"):
      return False
  return default


def question_type(q):
  t = q.get("type") if isinstance(q, dict) else None
  return t if isinstance(t, str) and t else "mcq"


def normalize_loaded(data):
  """Chuẩn hóa tối thiểu để giao diện không bị crash.

  Trả về chuỗi lỗi nếu file không dùng được, ngược lại trả về None.
  """
  topics = data.setdefault("topics", [])
  if not isinstance(topics, list):
    return "'topics' must be an array."
  return None


def find_problems(data):
  """Liệt kê các chỗ sai cấu trúc để báo cho người dùng sau khi mở file."""
  problems = []
  seen_ids = set()
  for i, t in enumerate(as_list(data.get("topics")), 1):
    if not isinstance(t, dict):
      problems.append(
          f"Topic {i}: not an object ({json_type_name(t)}) - kept unchanged,"
          " read-only"
      )
      continue
    tid = t.get("id")
    if tid in seen_ids and tid is not None:
      problems.append(f"Topic {i}: duplicate id '{clip(tid, 30)}'")
    seen_ids.add(tid)
    for key in ("notes", "key_terms", "flashcards", "questions"):
      if key in t and not isinstance(t[key], list):
        problems.append(
            f"Topic {i}: '{key}' is not an array ({json_type_name(t[key])})"
        )
      else:
        bad = [x for x in as_list(t.get(key)) if not isinstance(x, dict)]
        if bad and key != "questions":
          problems.append(
              f"Topic {i}: {len(bad)} item(s) in '{key}' are not objects"
              " (shown as empty rows)"
          )
    for j, q in enumerate(as_list(t.get("questions")), 1):
      tag = f"Topic {i} Q{j}"
      if not isinstance(q, dict):
        problems.append(
            f"{tag}: not an object ({json_type_name(q)}) - kept unchanged,"
            " read-only"
        )
        continue
      qt = q.get("type")
      if qt is None:
        problems.append(f"{tag}: missing 'type' (edited as mcq)")
      elif qt not in QUESTION_TYPES:
        problems.append(f"{tag}: unknown type '{clip(qt, 20)}'")
      eff = question_type(q)
      if eff == "mcq":
        opts = q.get("options")
        if not isinstance(opts, list) or len(opts) < 2:
          problems.append(f"{tag}: fewer than 2 options")
        try:
          ans = int(q.get("answer", 0))
          if isinstance(opts, list) and not 0 <= ans < len(opts):
            problems.append(f"{tag}: answer index {ans} is out of range")
        except (TypeError, ValueError):
          problems.append(f"{tag}: answer is not an integer")
      elif eff == "truefalse" and not isinstance(q.get("answer"), bool):
        problems.append(f"{tag}: answer is not true/false")
  return problems


# ----------------------------------------------------------------------
# Widget dùng chung
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


def banner_label(text, kind="warn"):
  """Hộp thông báo; kind = 'warn' (vàng) hoặc 'error' (đỏ)."""
  label = QLabel(text)
  label.setWordWrap(True)
  label.setProperty("banner", kind)
  label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
  return label


def make_form(parent=None):
  form = QFormLayout(parent) if parent is not None else QFormLayout()
  form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
  form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
  form.setVerticalSpacing(8)
  return form


def index_items(listw):
  """Ghi chỉ số hiện tại của mỗi dòng vào item (để biết thứ tự sau khi kéo thả)."""
  for i in range(listw.count()):
    listw.item(i).setData(Qt.ItemDataRole.UserRole, i)


def set_list_items(listw, labels):
  """Nạp lại QListWidget mà không phát tín hiệu chọn."""
  listw.blockSignals(True)
  listw.clear()
  if labels:
    listw.addItems(labels)
  index_items(listw)
  listw.blockSignals(False)


def locate_json_error(text, err):
  """Tìm (dòng, cột) đáng đổ lỗi nhất cho một JSONDecodeError.

  Với lỗi thiếu dấu phẩy/hai chấm, json báo vị trí ở token kế tiếp (đầu dòng
  sau); thực tế dòng sai là dòng trước đó nên lùi về ký tự cuối của dòng ấy.
  Với dấu phẩy thừa trước } hoặc ] thì chỉ vào dấu phẩy.
  """
  pos = min(max(err.pos, 0), len(text))
  if err.msg.startswith("Expecting") and "delimiter" in err.msg:
    j = pos
    while j > 0 and text[j - 1] in " \t\r\n":
      j -= 1
    if j < pos and "\n" in text[j:pos]:
      pos = max(j - 1, 0)
  elif text[pos : pos + 1] in ("}", "]"):
    # Dấu phẩy thừa trước } hoặc ]: chỉ vào chính dấu phẩy đó.
    j = pos
    while j > 0 and text[j - 1] in " \t\r\n":
      j -= 1
    if j > 0 and text[j - 1] == ",":
      pos = j - 1
  line = text.count("\n", 0, pos) + 1
  col = pos - (text.rfind("\n", 0, pos) + 1) + 1
  return line, col


def select_row_silently(listw, row):
  listw.blockSignals(True)
  listw.setCurrentRow(row)
  listw.blockSignals(False)
  listw.scrollToItem(listw.item(row))


class ReorderList(QListWidget):
  """Danh sách kéo thả để đổi thứ tự.

  Mỗi item giữ chỉ số gốc trong Qt.UserRole (xem index_items). Sau khi thả,
  phát tín hiệu `reordered` kèm thứ tự mới (danh sách chỉ số gốc).
  """

  reordered = pyqtSignal(list)

  def __init__(self):
    super().__init__()
    self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self.setDragEnabled(True)
    self.setAcceptDrops(True)
    self.setDropIndicatorShown(True)
    self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    self.setDefaultDropAction(Qt.DropAction.MoveAction)

  def dropEvent(self, event):
    self.blockSignals(True)  # không để currentRowChanged chạy giữa chừng
    try:
      super().dropEvent(event)
    finally:
      self.blockSignals(False)
    order = [
        self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())
    ]
    if order != list(range(self.count())):
      self.reordered.emit(order)


class DragHandle(QLabel):
  """Tay nắm để kéo một hàng trong ScrollList."""

  def __init__(self, scroll, row):
    super().__init__("⋮⋮")
    self._scroll = scroll
    self._row = row
    self.setCursor(Qt.CursorShape.OpenHandCursor)
    self.setToolTip("Drag to reorder")
    self.setFixedSize(24, 28)
    self.setAlignment(Qt.AlignmentFlag.AlignCenter)

  def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
      self._scroll.begin_drag(self._row)
      event.accept()

  def mouseMoveEvent(self, event):
    self._scroll.update_drag(event.globalPosition().toPoint())

  def mouseReleaseEvent(self, event):
    self._scroll.end_drag()


class ScrollList(QScrollArea):
  """Khung cuộn dọc chứa danh sách hàng.

  Danh sách dài được dựng theo từng đợt (QTimer) và tắt vẽ lại trong lúc dựng
  nên giao diện không bị đứng.
  """

  def __init__(self):
    super().__init__()
    self.setWidgetResizable(True)
    self.setFrameShape(QFrame.Shape.NoFrame)
    self.viewport().setAutoFillBackground(False)
    self.inner = QWidget()
    self.inner.setAutoFillBackground(False)
    self.vbox = QVBoxLayout(self.inner)
    self.vbox.setContentsMargins(4, 4, 8, 4)
    self.vbox.setSpacing(8)
    self.vbox.addStretch(1)  # luôn nằm cuối, đẩy các hàng lên trên
    self.setWidget(self.inner)

    self._items = []
    self._pos = 0
    self._build_row = None
    self._timer = QTimer(self)
    self._timer.setSingleShot(True)
    self._timer.setInterval(1)
    self._timer.timeout.connect(self._build_step)

    # Kéo thả đổi thứ tự hàng (qua DragHandle)
    self.on_reorder = None  # callback không đối số, gọi sau khi đổi thứ tự
    self._drag_row = None
    self._drop_index = None
    self._indicator = None

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

  # --- Kéo thả đổi thứ tự ---
  def row_widgets(self):
    return [self.vbox.itemAt(i).widget() for i in range(self.vbox.count() - 1)]

  def begin_drag(self, row):
    self._drag_row = row
    self._drop_index = None
    if self._indicator is None:
      self._indicator = QFrame(self.inner)
      self._indicator.setFixedHeight(3)
      self._indicator.setAutoFillBackground(True)
      self._indicator.setBackgroundRole(QPalette.ColorRole.Highlight)
    QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)

  def update_drag(self, global_pos):
    if self._drag_row is None:
      return
    y = self.inner.mapFromGlobal(global_pos).y()
    others = [w for w in self.row_widgets() if w is not self._drag_row]
    if others:
      idx = sum(1 for w in others if y > w.geometry().center().y())
      self._drop_index = idx
      gap = self.vbox.spacing() // 2
      if idx < len(others):
        top = others[idx].geometry().top() - gap
      else:
        top = others[-1].geometry().bottom() + gap
      self._indicator.setGeometry(0, top - 1, self.inner.width(), 3)
      self._indicator.show()
      self._indicator.raise_()
    # Tự cuộn khi kéo sát mép trên/dưới
    vy = self.viewport().mapFromGlobal(global_pos).y()
    bar = self.verticalScrollBar()
    if vy < 28:
      bar.setValue(bar.value() - 14)
    elif vy > self.viewport().height() - 28:
      bar.setValue(bar.value() + 14)

  def end_drag(self):
    row, idx = self._drag_row, self._drop_index
    self._drag_row = None
    QApplication.restoreOverrideCursor()
    if self._indicator is not None:
      self._indicator.hide()
    if row is None or idx is None:
      return
    if idx == self.row_widgets().index(row):
      return
    self.vbox.removeWidget(row)
    self.vbox.insertWidget(idx, row)
    if self.on_reorder is not None:
      self.on_reorder()

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
    self._dirty = False  # có thay đổi chưa lưu
    self._rendering_json = False  # đang nạp JSON vào ô Text (không tính là sửa)

    self.theme_mode = DEFAULT_THEME_MODE
    self._effective_theme = None
    self._last_theme_check = 0.0

    # Tab nào đang hiển thị đúng dữ liệu của chủ đề hiện tại (nạp lười)
    self._tab_loaded = {key: False for key in TAB_KEYS}
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []

    self.apply_theme()  # trước khi dựng widget để chỉ polish QSS một lần
    self.create_widgets()
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
    p = PALETTES[effective]
    app = QApplication.instance()
    app.setPalette(build_palette(p))
    app.setStyleSheet(STYLE_TEMPLATE.substitute(p))
    if self.isVisible():
      self.apply_titlebar()

  def apply_titlebar(self):
    p = PALETTES[self._effective_theme]
    set_titlebar(
        int(self.winId()), self._effective_theme == "dark", p["bg"], p["fg"]
    )

  def showEvent(self, event):
    super().showEvent(event)
    self.apply_titlebar()

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
    if self._dirty and not name:
      name = "Untitled"
    mark = "● " if self._dirty else ""
    self.setWindowTitle(f"{mark}{name} - {APP_NAME}" if name else APP_NAME)

  def new_line(self, text=""):
    """QLineEdit báo 'chưa lưu' khi người dùng gõ (không tính setText)."""
    edit = QLineEdit(text)
    edit.textEdited.connect(self.mark_dirty)
    return edit

  # ------------------------------------------------------------------
  # Trạng thái "chưa lưu"
  # ------------------------------------------------------------------
  def mark_dirty(self, *_args):
    if not self._dirty:
      self.set_dirty(True)

  def set_dirty(self, dirty):
    if dirty == self._dirty:
      return
    self._dirty = dirty
    self.refresh_badge()
    self.update_title()

  def refresh_badge(self):
    badge = self.badge
    badge.setText("● Unsaved changes" if self._dirty else "✓ All changes saved")
    badge.setToolTip("Click to save (Ctrl+S)" if self._dirty else "")
    badge.setProperty("badge", "dirty" if self._dirty else "clean")
    badge.style().unpolish(badge)
    badge.style().polish(badge)

  def on_badge_clicked(self, _checked=False):
    if self._dirty:
      self.save_file()

  def confirm_discard(self):
    """Hỏi lưu nếu có thay đổi chưa lưu. Trả về False nếu người dùng hủy."""
    if not self._dirty:
      return True
    answer = QMessageBox.question(
        self,
        "Unsaved changes",
        "You have unsaved changes. Save them first?",
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Save,
    )
    if answer == QMessageBox.StandardButton.Cancel:
      return False
    if answer == QMessageBox.StandardButton.Save:
      self.save_file()
      return not self._dirty  # lưu bị hủy/lỗi thì ở lại
    return True

  def closeEvent(self, event):
    if self.confirm_discard():
      event.accept()
    else:
      event.ignore()

  def copy_json(self):
    """Chép toàn bộ JSON vào clipboard (ở chế độ Text: chép đúng nội dung ô)."""
    if self.mode == "Text":
      text = self.json_text.toPlainText()
    else:
      self.commit_meta()
      self.commit_current_topic()
      text = json.dumps(self.data, ensure_ascii=False, indent=2)
    QGuiApplication.clipboard().setText(text)
    self.set_status(f"JSON copied to clipboard ({len(text):,} characters).")

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
    self.add_menu_action(file_menu, "Copy JSON", self.copy_json, "Ctrl+Shift+C")
    file_menu.addSeparator()
    self.add_menu_action(file_menu, "Exit", self.close)

    # Chỉ báo chưa lưu ở góc phải thanh menu; bấm vào để lưu.
    corner = QWidget()
    corner_h = QHBoxLayout(corner)
    corner_h.setContentsMargins(0, 2, 8, 2)
    self.badge = QPushButton()
    self.badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    self.badge.setProperty("badge", "clean")
    self.badge.clicked.connect(self.on_badge_clicked)
    corner_h.addWidget(self.badge)
    self.menuBar().setCornerWidget(corner, Qt.Corner.TopRightCorner)
    self.refresh_badge()

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setContentsMargins(8, 4, 8, 8)
    self.setCentralWidget(splitter)

    # --- Cột trái: metadata và danh sách topic ---
    left = QWidget()
    left_v = QVBoxLayout(left)
    left_v.setContentsMargins(0, 0, 0, 0)
    left_v.setSpacing(6)

    meta_box = QGroupBox("General Information")
    meta_form = make_form(meta_box)
    self.meta_entries = {}
    for label, key in (
        ("Title:", "title"),
        ("Subject:", "subject"),
        ("Level:", "level"),
        ("Language:", "language"),
    ):
      ent = self.new_line()
      ent.editingFinished.connect(
          lambda k=key, e=ent: self.update_meta(k, e)
      )
      meta_form.addRow(label, ent)
      self.meta_entries[key] = ent
    left_v.addWidget(meta_box)

    topic_box = QGroupBox("Topics")
    topic_v = QVBoxLayout(topic_box)
    topic_v.setSpacing(8)
    self.topic_list = ReorderList()
    self.topic_list.currentRowChanged.connect(self.on_select_topic)
    self.topic_list.reordered.connect(self.on_topics_reordered)
    topic_v.addWidget(self.topic_list, 1)
    btn_row = QHBoxLayout()
    add_btn = make_button("Add Topic")
    add_btn.clicked.connect(self.add_topic)
    del_btn = make_button("Delete Topic")
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
    splitter.setSizes([280, 1020])

    self.init_editor_workspace()
    self.init_settings_tab()

  def init_editor_workspace(self):
    root = QVBoxLayout(self.tab_editor)
    root.setContentsMargins(12, 10, 12, 12)
    root.setSpacing(8)

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
    copy_btn = make_button("Copy JSON")
    copy_btn.setToolTip("Copy the whole pack as JSON (Ctrl+Shift+C)")
    copy_btn.clicked.connect(lambda _c=False: self.copy_json())
    mode_row.addWidget(copy_btn)
    root.addLayout(mode_row)

    self.stack = QStackedWidget()
    root.addWidget(self.stack, 1)

    # --- View 1: Plain text ---
    self.text_page = QWidget()
    text_v = QVBoxLayout(self.text_page)
    text_v.setContentsMargins(0, 0, 0, 0)
    self.json_text = QPlainTextEdit()
    self.json_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    self.json_text.setFont(self.mono_font())
    text_v.addWidget(self.json_text, 1)
    self.json_error_bar = banner_label("", "error")
    self.json_error_bar.hide()
    text_v.addWidget(self.json_error_bar)
    self.json_text.textChanged.connect(self.clear_json_error)
    self.json_text.document().modificationChanged.connect(self.on_json_modified)
    apply_row = QHBoxLayout()
    apply_row.addStretch(1)
    apply_btn = make_button("Apply Changes", primary=True)
    apply_btn.clicked.connect(self.apply_plain_text)
    apply_row.addWidget(apply_btn)
    text_v.addLayout(apply_row)
    self.stack.addWidget(self.text_page)

    # --- View 2: Form ---
    self.gui_page = QWidget()
    gui_v = QVBoxLayout(self.gui_page)
    gui_v.setContentsMargins(0, 0, 0, 0)
    gui_v.setSpacing(8)

    self.invalid_banner = banner_label("")
    self.invalid_banner.hide()
    gui_v.addWidget(self.invalid_banner)

    self.info_holder = QWidget()
    info = QGridLayout(self.info_holder)
    info.setContentsMargins(0, 0, 0, 0)
    info.setHorizontalSpacing(8)
    info.setVerticalSpacing(8)
    self.t_id_ent = self.new_line()
    self.t_id_ent.setFixedWidth(100)
    self.t_title_ent = self.new_line()
    self.t_summary_ent = self.new_line()
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
    gui_v.addWidget(self.info_holder)

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

  @staticmethod
  def mono_font():
    families = set(QFontDatabase.families())
    for fam in ("Cascadia Mono", "Cascadia Code", "Consolas"):
      if fam in families:
        font = QFont(fam)
        break
    else:
      font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(10)
    return font

  def init_settings_tab(self):
    outer = QVBoxLayout(self.tab_settings)
    outer.setContentsMargins(12, 10, 12, 12)
    box = QGroupBox("Appearance")
    box_v = QVBoxLayout(box)
    box_v.setSpacing(8)
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
    self._rendering_json = True
    try:
      self.json_text.setPlainText(
          json.dumps(self.data, ensure_ascii=False, indent=2)
      )
      self.json_text.document().setModified(False)
    finally:
      self._rendering_json = False
    self.clear_json_error()

  def on_json_modified(self, modified):
    if modified and not self._rendering_json:
      self.mark_dirty()

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
      self.show_json_error(raw, e)
      return None
    if not isinstance(parsed, dict):
      self.show_json_error(raw, None, "A study pack must be a JSON object.")
      return None
    error = normalize_loaded(parsed)
    if error:
      self.show_json_error(raw, None, error)
      return None
    self.clear_json_error()
    return parsed

  def show_json_error(self, raw, err, message=None):
    """Báo lỗi ngay trong ô Text: tô dòng sai, đặt con trỏ, hiện thông báo."""
    if err is not None:
      line, col = locate_json_error(raw, err)
      text = f"Line {line}, column {col}: {err.msg}"
      self.highlight_json_line(line, col)
    else:
      text = message
      self.json_text.setExtraSelections([])
    self.json_error_bar.setText(text)
    self.json_error_bar.show()
    self.set_status(f"JSON error - {text}", 8000)

  def highlight_json_line(self, line, col):
    block = self.json_text.document().findBlockByNumber(line - 1)
    if not block.isValid():
      return
    color = QColor(PALETTES[self._effective_theme]["err_border"])
    color.setAlpha(80)
    sel = QTextEdit.ExtraSelection()
    sel.format.setBackground(color)
    sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
    sel.cursor = QTextCursor(block)
    self.json_text.setExtraSelections([sel])

    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + min(col - 1, max(block.length() - 1, 0)))
    self.json_text.setTextCursor(cursor)
    self.json_text.centerCursor()
    self.json_text.setFocus()

  def clear_json_error(self):
    self.json_text.setExtraSelections([])
    self.json_error_bar.hide()

  def apply_plain_text(self):
    parsed = self.parse_pack_text(self.json_text.toPlainText())
    if parsed is None:
      return
    self.data = parsed
    self.refresh_ui()
    self.mark_dirty()
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

  def current_topic(self):
    """Topic đang mở nếu hợp lệ (là object), ngược lại None."""
    idx = self.current_topic_index
    topics = self.data.get("topics")
    if idx is None or not isinstance(topics, list) or idx >= len(topics):
      return None
    t = topics[idx]
    return t if isinstance(t, dict) else None

  @staticmethod
  def assign_list(t, key, new_list):
    # Chỉ xem tab không được làm mất trường sai kiểu (vd. "notes": "text").
    if not new_list and key in t and not isinstance(t[key], list):
      return
    t[key] = new_list

  def commit_current_topic(self):
    """Ghi form của chủ đề đang mở về self.data (chỉ ở chế độ GUI)."""
    t = self.current_topic()
    if t is None or self.mode != "GUI":
      return
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
      self.assign_list(t, "notes", self.collect_notes())
    if self._tab_loaded["terms"]:
      self.assign_list(t, "key_terms", self.collect_terms())
    if self._tab_loaded["flashcards"]:
      self.assign_list(t, "flashcards", self.collect_flashcards())
    if self._tab_loaded["questions"]:
      self.save_current_question_form(silent=True)

  def new_file(self):
    if not self.confirm_discard():
      return
    self.data = self.empty_pack()
    self.current_path = None
    self.refresh_ui()
    self.set_dirty(False)
    self.update_title()

  def open_file(self):
    if not self.confirm_discard():
      return
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
      error = normalize_loaded(data)
      if error:
        raise ValueError(error)
    except Exception as e:
      QMessageBox.critical(self, "Error", f"Failed to read file:\n{e}")
      return
    self.data = data
    self.current_path = file_path
    self.refresh_ui()
    self.set_dirty(False)
    self.update_title()
    self.set_status(f"File loaded: {os.path.basename(file_path)}")
    self.report_problems(file_path)

  def report_problems(self, file_path):
    problems = find_problems(self.data)
    if not problems:
      return
    shown = problems[:12]
    more = len(problems) - len(shown)
    text = "\n".join(f"• {p}" for p in shown)
    if more > 0:
      text += f"\n… and {more} more"
    box = QMessageBox(self)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("File loaded with issues")
    box.setText(
        f"{os.path.basename(file_path)} has {len(problems)} structural "
        "issue(s). The editor opened it anyway:"
    )
    box.setInformativeText(text)
    box.exec()

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
    self.set_dirty(False)
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
    if not isinstance(t, dict):
      return f"⚠ Invalid item ({json_type_name(t)})"
    return clip(f"{t.get('id', '')}: {t.get('title', 'Untitled')}")

  def refresh_topic_list(self):
    set_list_items(
        self.topic_list,
        [self.topic_label(t) for t in as_list(self.data.get("topics"))],
    )

  def refresh_topic_list_item(self):
    idx = self.current_topic_index
    t = self.current_topic()
    if idx is None or t is None:
      return
    item = self.topic_list.item(idx)
    if item is not None:
      item.setText(self.topic_label(t))

  def invalidate_tabs(self):
    for key in self._tab_loaded:
      self._tab_loaded[key] = False
    self.current_question_index = None

  def clear_tab_views(self):
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []
    self.notes_view.clear()
    self.terms_view.clear()
    self.fc_view.clear()
    set_list_items(self.q_list, [])
    self.q_detail.clear()

  def set_topic_form_valid(self, valid, raw=None):
    """Bật/tắt form; hiện cảnh báo khi topic không phải object."""
    self.invalid_banner.setVisible(not valid)
    self.info_holder.setEnabled(valid)
    self.topic_tabs.setEnabled(valid)
    if not valid:
      self.invalid_banner.setText(
          f"This item is not a valid topic object ({json_type_name(raw)}: "
          f"{clip(repr(raw), 60)}). It is kept unchanged in the file. "
          "Use Plain Text mode to fix or remove it."
      )

  def reset_topic_view(self):
    """Xóa trạng thái chủ đề đang mở (khi đổi dữ liệu hoặc xóa topic)."""
    self.current_topic_index = None
    self.invalidate_tabs()
    for ent in (self.t_id_ent, self.t_title_ent, self.t_summary_ent):
      ent.clear()
    self.clear_tab_views()
    self.set_topic_form_valid(True)

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
    index_items(self.topic_list)
    self.topic_list.blockSignals(False)
    select_row_silently(self.topic_list, idx)
    self.on_select_topic()
    self.mark_dirty()
    if self.mode == "Text":
      self.render_json_text()

  def delete_topic(self):
    row = self.topic_list.currentRow()
    if row < 0:
      return
    del self.data["topics"][row]
    self.reset_topic_view()
    self.refresh_topic_list()
    self.mark_dirty()
    if self.mode == "Text":
      self.render_json_text()

  def on_topics_reordered(self, order):
    """Người dùng kéo thả topic: đổi thứ tự trong self.data tương ứng."""
    topics = self.data.get("topics")
    if not isinstance(topics, list) or sorted(order) != list(range(len(topics))):
      self.refresh_topic_list()
      if self.current_topic_index is not None:
        select_row_silently(self.topic_list, self.current_topic_index)
      return
    self.commit_current_topic()
    old = self.current_topic_index
    topics[:] = [topics[i] for i in order]
    index_items(self.topic_list)
    if old is not None:
      self.current_topic_index = order.index(old)
      select_row_silently(self.topic_list, self.current_topic_index)
    self.mark_dirty()
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
    t = self.current_topic()
    if t is None:
      return
    value = entry.text()
    if t.get(field, "") == value:
      return
    t[field] = value
    if field in ("id", "title"):
      self.refresh_topic_list_item()

  def load_topic_gui_data(self):
    idx = self.current_topic_index
    if idx is None:
      return
    t = self.current_topic()
    if t is None:
      topics = as_list(self.data.get("topics"))
      raw = topics[idx] if idx < len(topics) else None
      for ent in (self.t_id_ent, self.t_title_ent, self.t_summary_ent):
        ent.clear()
      self.clear_tab_views()
      self.set_topic_form_valid(False, raw)
      return
    self.set_topic_form_valid(True)
    self.t_id_ent.setText(str(t.get("id", "")))
    self.t_title_ent.setText(str(t.get("title", "")))
    self.t_summary_ent.setText(str(t.get("summary", "")))
    self.load_visible_tab()

  def load_visible_tab(self):
    """Nạp dữ liệu cho tab đang xem nếu chưa nạp."""
    t = self.current_topic()
    if t is None or self.mode != "GUI":
      return
    key = TAB_KEYS[self.topic_tabs.currentIndex()]
    if self._tab_loaded[key]:
      return
    if key == "notes":
      self.load_notes_ui(as_list(t.get("notes")))
    elif key == "terms":
      self.load_terms_ui(as_list(t.get("key_terms")))
    elif key == "flashcards":
      self.load_flashcards_ui(as_list(t.get("flashcards")))
    else:
      self.load_questions_list()
    self._tab_loaded[key] = True

  # ------------------------------------------------------------------
  # Thanh điều khiển dùng chung cho các tab Notes/Terms/Flashcards
  # ------------------------------------------------------------------
  def make_list_tab(self, tab, add_text, add_slot, save_text, save_slot):
    v = QVBoxLayout(tab)
    v.setContentsMargins(10, 10, 10, 10)
    top = QHBoxLayout()
    add_btn = make_button(add_text)
    add_btn.clicked.connect(add_slot)
    save_btn = make_button(save_text, primary=True)
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
    sec = as_dict(sec)
    group = QGroupBox(f"Section {len(self.note_widgets) + 1}")
    v = QVBoxLayout(group)
    v.setSpacing(8)

    head = QHBoxLayout()
    head.addWidget(QLabel("Heading:"))
    h_ent = self.new_line(str(sec.get("heading", "")))
    head.addWidget(h_ent, 1)
    del_btn = make_icon_button("\uE74D", "✕", "Delete section")
    del_btn.clicked.connect(
        lambda _c=False, g=group: self.remove_note_section(g)
    )
    head.addWidget(del_btn)
    v.addLayout(head)

    v.addWidget(QLabel("Points:"))
    points = sec.get("points", [])
    if isinstance(points, list):
      text = "\n".join(str(p) for p in points)
    elif isinstance(points, str):
      text = points
    else:
      text = ""
    p_txt = QPlainTextEdit()
    p_txt.setTabChangesFocus(True)
    p_txt.setPlainText(text)
    p_txt.document().setModified(False)
    p_txt.document().modificationChanged.connect(self.mark_dirty)
    p_txt.setFixedHeight(p_txt.fontMetrics().lineSpacing() * 4 + 20)
    v.addWidget(p_txt)

    self.note_widgets.append((h_ent, p_txt, group))
    return group

  def add_note_section(self):
    if self.current_topic() is None:
      return
    self.notes_view.append(
        {"heading": "New Section", "points": ["Point about **term**."]}
    )
    self.mark_dirty()

  def remove_note_section(self, group):
    self.note_widgets = [w for w in self.note_widgets if w[2] is not group]
    self.notes_view.remove_widget(group)
    self.mark_dirty()

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
    t = self.current_topic()
    if t is None:
      return
    self.assign_list(t, "notes", self.collect_notes())
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
    item = as_dict(item)
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(2, 2, 2, 2)
    h.addWidget(fixed_label(f"Term {len(self.term_widgets) + 1}:", 60))
    t_ent = self.new_line(str(item.get("term", "")))
    t_ent.setMinimumWidth(170)
    h.addWidget(t_ent, 1)
    h.addWidget(fixed_label("Def:", 32))
    d_ent = self.new_line(str(item.get("definition", "")))
    h.addWidget(d_ent, 3)
    del_btn = make_icon_button("\uE74D", "✕", "Delete term")
    del_btn.clicked.connect(lambda _c=False, r=row: self.remove_term_row(r))
    h.addWidget(del_btn)
    self.term_widgets.append((t_ent, d_ent, row))
    return row

  def add_term_row(self):
    if self.current_topic() is None:
      return
    self.terms_view.append({"term": "New Term", "definition": "Definition here."})
    self.mark_dirty()

  def remove_term_row(self, row):
    self.term_widgets = [w for w in self.term_widgets if w[2] is not row]
    self.terms_view.remove_widget(row)
    self.mark_dirty()

  def collect_terms(self):
    self.terms_view.flush()
    return [
        {"term": t_ent.text(), "definition": d_ent.text()}
        for t_ent, d_ent, _ in self.term_widgets
    ]

  def save_terms_form(self):
    t = self.current_topic()
    if t is None:
      return
    self.assign_list(t, "key_terms", self.collect_terms())
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
    self.fc_view.on_reorder = self.on_fc_reordered

  def load_flashcards_ui(self, fc_list):
    self.fc_widgets = []
    self.fc_view.populate(fc_list, self.build_fc_row)

  def build_fc_row(self, fc):
    fc = as_dict(fc)
    group = QGroupBox(f"Flashcard {len(self.fc_widgets) + 1}")
    v = QVBoxLayout(group)
    v.setSpacing(8)
    form = make_form()
    f_ent = self.new_line(str(fc.get("front", "")))
    b_ent = self.new_line(str(fc.get("back", "")))
    form.addRow("Front:", f_ent)
    form.addRow("Back:", b_ent)
    v.addLayout(form)
    btn_row = QHBoxLayout()
    btn_row.addWidget(DragHandle(self.fc_view, group))
    btn_row.addStretch(1)
    del_btn = make_icon_button("\uE74D", "✕", "Delete flashcard")
    del_btn.clicked.connect(lambda _c=False, g=group: self.remove_fc_row(g))
    btn_row.addWidget(del_btn)
    v.addLayout(btn_row)
    self.fc_widgets.append((f_ent, b_ent, group))
    return group

  def add_fc_row(self):
    if self.current_topic() is None:
      return
    self.fc_view.append({"front": "Question?", "back": "Answer."})
    self.mark_dirty()

  def remove_fc_row(self, group):
    self.fc_widgets = [w for w in self.fc_widgets if w[2] is not group]
    self.fc_view.remove_widget(group)
    self.renumber_fc()
    self.mark_dirty()

  def on_fc_reordered(self):
    """Hàng flashcard vừa được kéo thả: đồng bộ danh sách widget theo thứ tự mới."""
    order = self.fc_view.row_widgets()
    self.fc_widgets.sort(key=lambda w: order.index(w[2]))
    self.renumber_fc()
    self.mark_dirty()

  def renumber_fc(self):
    for i, (_f, _b, group) in enumerate(self.fc_widgets):
      group.setTitle(f"Flashcard {i + 1}")

  def collect_flashcards(self):
    self.fc_view.flush()
    return [
        {"front": f_ent.text(), "back": b_ent.text()}
        for f_ent, b_ent, _ in self.fc_widgets
    ]

  def save_fc_form(self):
    t = self.current_topic()
    if t is None:
      return
    self.assign_list(t, "flashcards", self.collect_flashcards())
    self.set_status("Flashcards updated.")

  # ------------------------------------------------------------------
  # 4. Questions
  # ------------------------------------------------------------------
  def init_questions_gui(self):
    outer = QVBoxLayout(self.tab_questions)
    outer.setContentsMargins(10, 10, 10, 10)
    splitter = QSplitter(Qt.Orientation.Horizontal)
    outer.addWidget(splitter)

    left = QWidget()
    left_v = QVBoxLayout(left)
    left_v.setContentsMargins(0, 0, 0, 0)
    left_v.setSpacing(8)
    left_v.addWidget(bold_label("Questions List"))
    self.q_list = ReorderList()
    self.q_list.currentRowChanged.connect(self.on_select_question_item)
    self.q_list.reordered.connect(self.on_questions_reordered)
    left_v.addWidget(self.q_list, 1)

    ctrl = QHBoxLayout()
    self.q_type_combo = QComboBox()
    self.q_type_combo.addItems(list(QUESTION_TYPES))
    add_btn = make_button("+ Add")
    add_btn.clicked.connect(self.add_single_question)
    del_btn = make_button("Delete")
    del_btn.clicked.connect(self.delete_single_question)
    ctrl.addWidget(self.q_type_combo, 1)
    ctrl.addWidget(add_btn)
    ctrl.addWidget(del_btn)
    left_v.addLayout(ctrl)

    right = QWidget()
    right_v = QVBoxLayout(right)
    right_v.setContentsMargins(0, 0, 0, 0)
    right_v.setSpacing(8)
    self.q_detail = ScrollList()
    right_v.addWidget(self.q_detail, 1)
    save_row = QHBoxLayout()
    save_row.addStretch(1)
    save_btn = make_button("Save Question Changes", primary=True)
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
    if not isinstance(q, dict):
      return f"Q{idx + 1} [invalid]: {json_type_name(q)}"
    prompt = str(q.get("prompt", "")).replace("\n", " ")
    snippet = prompt[:35] + ("..." if len(prompt) > 35 else "")
    return f"Q{idx + 1} [{clip(question_type(q), 12)}]: {snippet}"

  def current_questions(self):
    t = self.current_topic()
    if t is None:
      return []
    return as_list(t.get("questions"))

  def load_questions_list(self):
    self.current_question_index = None
    self.q_detail.clear()
    questions = self.current_questions()
    set_list_items(
        self.q_list, [self.question_label(i, q) for i, q in enumerate(questions)]
    )

  def on_questions_reordered(self, order):
    """Người dùng kéo thả câu hỏi: đổi thứ tự trong self.data tương ứng."""
    questions = self.current_questions()
    if sorted(order) != list(range(len(questions))):
      self.load_questions_list()
      return
    self.save_current_question_form(silent=True)  # lưu form trước khi đổi chỗ
    old = self.current_question_index
    questions[:] = [questions[i] for i in order]
    index_items(self.q_list)
    for i, q in enumerate(questions):  # nhãn có số thứ tự "Q1, Q2, ..."
      self.q_list.item(i).setText(self.question_label(i, q))
    if old is not None:
      self.current_question_index = order.index(old)
      select_row_silently(self.q_list, self.current_question_index)
      self.render_single_question_form()  # cập nhật tiêu đề "Editing Question N"
    self.mark_dirty()
    if self.mode == "Text":
      self.render_json_text()

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
    questions = self.current_questions()
    idx = self.current_question_index
    if idx is None or idx >= len(questions):
      return
    q = questions[idx]

    self.q_detail.scroll_top()
    self.q_detail.freeze()
    try:
      if isinstance(q, dict):
        self.q_detail.add_widget(self.build_question_form(q))
      else:
        self.q_detail.add_widget(
            banner_label(
                f"This item is not a valid question object "
                f"({json_type_name(q)}: {clip(repr(q), 60)}). It is kept "
                "unchanged in the file. Use Plain Text mode to fix or remove it."
            )
        )
    finally:
      self.q_detail.thaw()

  def make_row_group(
      self,
      title,
      key,
      items,
      build_row,
      new_item,
      add_text,
      relabel=None,
      on_change=None,
  ):
    """Nhóm các dòng có thể thêm/xóa (lựa chọn, cặp nối, mệnh đề).

    build_row(item, layout, index) thêm widget vào layout và trả về tuple các
    widget giá trị. Danh sách các dòng lưu ở self.det_spec[key]; mỗi phần tử là
    (widget_dòng, *widget_giá_trị).
    """
    group = QGroupBox(title)
    group_v = QVBoxLayout(group)
    group_v.setSpacing(8)
    rows_v = QVBoxLayout()
    rows_v.setSpacing(6)
    group_v.addLayout(rows_v)
    entries = []
    self.det_spec[key] = entries

    def add_row(item):
      row = QWidget()
      h = QHBoxLayout(row)
      h.setContentsMargins(0, 0, 0, 0)
      parts = build_row(item, h, len(entries))
      del_btn = make_icon_button("\uE74D", "✕", "Remove")
      del_btn.clicked.connect(lambda _c=False, r=row: remove_row(r))
      h.addWidget(del_btn)
      rows_v.addWidget(row)
      entries.append((row,) + tuple(parts))

    def remove_row(row):
      for i, entry in enumerate(entries):
        if entry[0] is row:
          del entries[i]
          break
      else:
        return
      rows_v.removeWidget(row)
      row.setParent(None)
      row.deleteLater()
      if relabel is not None:
        relabel(entries)
      if on_change is not None:
        on_change("remove", i, entries)
      self.mark_dirty()

    def on_add(_checked=False):
      add_row(new_item)
      if relabel is not None:
        relabel(entries)
      if on_change is not None:
        on_change("add", len(entries) - 1, entries)
      for w in entries[-1][1:]:  # focus vào ô nhập của dòng mới
        if isinstance(w, QLineEdit):
          w.setFocus()
          break
      self.mark_dirty()

    for item in items:
      add_row(item)
    add_btn = make_button(add_text)
    add_btn.clicked.connect(on_add)
    btn_row = QHBoxLayout()
    btn_row.addWidget(add_btn)
    btn_row.addStretch(1)
    group_v.addLayout(btn_row)
    return group

  def build_question_form(self, q):
    q_type = question_type(q)
    form_w = QWidget()
    v = QVBoxLayout(form_w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(8)
    v.addWidget(
        bold_label(
            f"Editing Question {self.current_question_index + 1} "
            f"[{clip(q_type, 20).upper()}]"
        )
    )

    form = make_form()
    v.addLayout(form)
    self.det_prompt_ent = self.new_line(str(q.get("prompt", "")))
    form.addRow("Prompt:", self.det_prompt_ent)

    self.det_spec = {"type": q_type}
    end_form = make_form()  # các dòng cuối form (đáp án, giải thích)

    if q_type == "mcq":
      self.det_mcq_context = self.new_line(str(q.get("context", "")))
      form.addRow("Context:", self.det_mcq_context)
      self.det_mcq_source = self.new_line(str(q.get("source", "")))
      form.addRow("Source:", self.det_mcq_source)

      opts = q.get("options")
      if not isinstance(opts, list):
        opts = ["", "", "", ""]
      try:
        ans = max(0, int(q.get("answer", 0)))
      except (TypeError, ValueError, OverflowError):
        ans = 0
      ans = min(ans, 2**31 - 1)
      self.det_ans_spin = QSpinBox()
      # Mở rộng khoảng để không âm thầm sửa đáp án nằm ngoài phạm vi.
      self.det_ans_spin.setRange(0, max(3, len(opts) - 1, ans))
      self.det_ans_spin.setValue(ans)
      self.det_ans_spin.setMaximumWidth(90)
      self.det_ans_spin.valueChanged.connect(self.mark_dirty)

      def build_opt(item, h, index):
        label = fixed_label(f"Option {index}:", 70)
        edit = self.new_line(str(item))
        h.addWidget(label)
        h.addWidget(edit, 1)
        return (label, edit)

      def relabel_opts(entries):
        for i, entry in enumerate(entries):
          entry[1].setText(f"Option {i}:")

      def opts_changed(kind, idx, entries):
        # Giữ "Correct Index" trỏ đúng lựa chọn sau khi thêm/xóa.
        spin = self.det_ans_spin
        last = max(len(entries) - 1, 0)
        value = spin.value()
        if kind == "remove" and idx < value:
          value -= 1
        spin.setMaximum(last)
        spin.setValue(min(value, last))

      v.addWidget(
          self.make_row_group(
              "Options",
              "opt_ents",
              opts,
              build_opt,
              "",
              "+ Add option",
              relabel_opts,
              opts_changed,
          )
      )
      end_form.addRow("Correct Index:", self.det_ans_spin)

    elif q_type == "truefalse":
      holder, self.det_tf_true = self.make_true_false(
          "True", "False", to_bool(q.get("answer", True))
      )
      form.addRow("Answer:", holder)

    elif q_type == "short":
      self.det_short_ent = self.new_line(str(q.get("answer", "")))
      form.addRow("Model Answer:", self.det_short_ent)

    elif q_type == "cloze":
      ans_list = q.get("answers", [])
      self.det_cloze_ent = self.new_line(
          ", ".join(str(a) for a in ans_list)
          if isinstance(ans_list, list)
          else str(ans_list)
      )
      form.addRow("Answers:", self.det_cloze_ent)

    elif q_type == "match":

      def build_pair(item, h, index):
        item = as_dict(item)
        l_ent = self.new_line(str(item.get("left", "")))
        l_ent.setMinimumWidth(160)
        r_ent = self.new_line(str(item.get("right", "")))
        h.addWidget(l_ent, 1)
        h.addWidget(QLabel("->"))
        h.addWidget(r_ent, 3)
        return (l_ent, r_ent)

      v.addWidget(
          self.make_row_group(
              "Pairs (Left : Right)",
              "pair_ents",
              as_list(q.get("pairs")),
              build_pair,
              {"left": "", "right": ""},
              "+ Add pair",
          )
      )

    elif q_type == "tfs":
      self.det_quote_ent = self.new_line(str(q.get("quote", "")))
      form.addRow("Quote:", self.det_quote_ent)
      self.det_tfs_source = self.new_line(str(q.get("source", "")))
      form.addRow("Source:", self.det_tfs_source)

      def build_statement(item, h, index):
        item = as_dict(item)
        txt_ent = self.new_line(str(item.get("text", "")))
        holder, t_rb = self.make_true_false(
            "T", "F", to_bool(item.get("answer", True))
        )
        h.addWidget(txt_ent, 1)
        h.addWidget(holder)
        return (txt_ent, t_rb)

      v.addWidget(
          self.make_row_group(
              "Statements & Answers",
              "tfs_item_ents",
              as_list(q.get("items")),
              build_statement,
              {"text": "", "answer": True},
              "+ Add statement",
          )
      )

    self.det_exp_ent = self.new_line(str(q.get("explanation", "")))
    end_form.addRow("Explanation:", self.det_exp_ent)
    v.addLayout(end_form)
    return form_w

  def make_true_false(self, true_text, false_text, is_true):
    """Cặp radio True/False; trả về (widget chứa, radio 'True')."""
    holder = QWidget()  # parent riêng => mỗi cặp là một nhóm loại trừ
    h = QHBoxLayout(holder)
    h.setContentsMargins(0, 0, 0, 0)
    t_rb = QRadioButton(true_text)
    f_rb = QRadioButton(false_text)
    t_rb.setChecked(is_true)
    f_rb.setChecked(not is_true)
    t_rb.toggled.connect(self.mark_dirty)
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
    idx = self.current_question_index
    questions = self.current_questions()
    if idx is None or idx >= len(questions):
      return
    q = questions[idx]
    if not isinstance(q, dict):  # câu sai kiểu: giữ nguyên, không có form
      return
    q_type = question_type(q)

    q["prompt"] = self.det_prompt_ent.text()
    q["explanation"] = self.det_exp_ent.text()

    if q_type == "mcq":
      q["options"] = [e[2].text() for e in self.det_spec["opt_ents"]]
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
          {"left": e[1].text(), "right": e[2].text()}
          for e in self.det_spec["pair_ents"]
      ]
    elif q_type == "tfs":
      q["quote"] = self.det_quote_ent.text()
      self.set_or_remove(q, "source", self.det_tfs_source.text())
      q["items"] = [
          {"text": e[1].text(), "answer": e[2].isChecked()}
          for e in self.det_spec["tfs_item_ents"]
      ]

    item = self.q_list.item(idx)
    if item is not None:
      item.setText(self.question_label(idx, q))

    if not silent:
      self.set_status("Question updated.")

  def add_single_question(self):
    t = self.current_topic()
    if t is None:
      return
    questions = t.get("questions")
    if not isinstance(questions, list):
      questions = t["questions"] = []

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
    index_items(self.q_list)
    self.q_list.blockSignals(False)
    select_row_silently(self.q_list, idx)
    self.on_select_question_item()
    self.mark_dirty()

  def delete_single_question(self):
    row = self.q_list.currentRow()
    questions = self.current_questions()
    if row < 0 or row >= len(questions):
      return
    del questions[row]
    self.load_questions_list()
    self.mark_dirty()


def apply_app_font(app):
  """Segoe UI Variable (Win11) / Segoe UI (Win10) cỡ 9pt như ứng dụng Windows."""
  if sys.platform != "win32":
    return
  families = set(QFontDatabase.families())
  for fam in ("Segoe UI Variable Text", "Segoe UI"):
    if fam in families:
      app.setFont(QFont(fam, 9))
      return


def main():
  app = QApplication(sys.argv)
  app.setApplicationName(APP_NAME)
  app.setStyle("Fusion")  # nền ổn định để QSS và QPalette vẽ lên
  apply_app_font(app)
  window = StudyPackEditor()
  window.show()
  sys.exit(app.exec())


if __name__ == "__main__":
  main()