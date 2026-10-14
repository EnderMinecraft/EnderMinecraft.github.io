"""Study Pack Editor - trình soạn thảo study pack (JSON)."""

import json
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
  import sv_ttk  # Sun Valley theme (phong cách Windows 11), không bắt buộc

  HAS_SUNVALLEY = True
except ImportError:
  HAS_SUNVALLEY = False

APP_NAME = "Study Pack Editor"
DEFAULT_THEME_MODE = "light"  # "light" | "dark" | "system"
ENABLE_DPI_AWARENESS = True  # chỉ áp dụng trên Windows
RESIZE_THROTTLE_MS = 50  # gộp các lần cập nhật layout khi đang kéo resize
BUILD_CHUNK = 20  # số dòng dựng mỗi đợt khi nạp danh sách dài

# Bảng màu khớp Sun Valley, dùng cho widget tk thuần (Canvas/Listbox/Text)
# vì các widget này không tự đổi màu theo theme của ttk.
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


def enable_dpi_awareness():
  """Không để Windows phóng to bitmap của cửa sổ (gây mờ và vẽ chồng khi resize)."""
  if sys.platform != "win32":
    return
  try:
    import ctypes

    try:
      ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
      ctypes.windll.user32.SetProcessDPIAware()
  except Exception:
    pass


def detect_system_theme():
  """Trả về 'dark' hoặc 'light' theo cài đặt của hệ điều hành."""
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


def style_classic_widget(widget, palette):
  """Áp màu theme cho các widget tk thuần."""
  if not palette:
    return
  cls = widget.winfo_class()
  if cls == "Canvas":
    widget.configure(bg=palette["bg"])
  elif cls in ("Listbox", "Text"):
    options = dict(
        bg=palette["field"],
        fg=palette["fg"],
        selectbackground=palette["accent"],
        selectforeground=palette["accent_fg"],
        highlightthickness=1,
        highlightbackground=palette["border"],
        highlightcolor=palette["accent"],
        relief="flat",
        borderwidth=0,
    )
    if cls == "Text":
      options["insertbackground"] = palette["fg"]
    widget.configure(**options)


def restyle_tree(widget, palette):
  style_classic_widget(widget, palette)
  for child in widget.winfo_children():
    restyle_tree(child, palette)


def replace_listbox_item(listbox, index, label):
  """Đổi nhãn một dòng mà không làm mất trạng thái chọn."""
  if listbox.get(index) == label:
    return
  selected = listbox.curselection()
  listbox.delete(index)
  listbox.insert(index, label)
  for s in selected:
    listbox.selection_set(s)


class ScrollFrame(ttk.Frame):
  """Khung cuộn dọc dựa trên Canvas.

  - Cập nhật layout khi resize được gộp lại để không bị lag/nhấp nháy.
  - Danh sách dài được dựng theo từng đợt nên giao diện không bị đứng.
  """

  def __init__(self, parent, padding=0):
    super().__init__(parent)
    self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
    self.vsb = ttk.Scrollbar(
        self, orient="vertical", command=self.canvas.yview
    )
    self.canvas.configure(yscrollcommand=self.vsb.set)
    self.vsb.pack(side="right", fill="y")
    self.canvas.pack(side="left", fill="both", expand=True)

    self.inner = ttk.Frame(self.canvas, padding=padding)
    self._win = self.canvas.create_window(
        (0, 0), window=self.inner, anchor="nw"
    )

    self._width = 0
    self._width_job = None
    self._region_job = None
    self._inner_size = None
    self._items = []
    self._pos = 0
    self._build_row = None
    self._build_job = None

    self.canvas.bind("<Configure>", self._on_canvas_configure)
    self.inner.bind("<Configure>", self._on_inner_configure)

  # --- Layout ---
  def _on_canvas_configure(self, event):
    if event.width <= 1 or event.width == self._width:
      return
    if self._width == 0:
      self._apply_width(event.width)
    elif self._width_job is None:
      self._width_job = self.after(RESIZE_THROTTLE_MS, self._flush_width)

  def _apply_width(self, width):
    self._width = width
    self.canvas.itemconfigure(self._win, width=width)

  def _flush_width(self):
    self._width_job = None
    width = self.canvas.winfo_width()
    if width > 1 and width != self._width:
      self._apply_width(width)

  def _on_inner_configure(self, event):
    size = (event.width, event.height)
    if size != self._inner_size:
      self._inner_size = size
      self._schedule_region()

  def _schedule_region(self):
    if self._region_job is None:
      self._region_job = self.after_idle(self._update_region)

  def _update_region(self):
    self._region_job = None
    bbox = self.canvas.bbox("all")
    if bbox:
      self.canvas.configure(scrollregion=bbox)

  def scroll_top(self):
    self.canvas.yview_moveto(0)

  def scroll_to_end(self):
    self.update_idletasks()
    self._update_region()
    self.canvas.yview_moveto(1.0)

  # --- Ẩn/hiện khi dựng nội dung (tránh vẽ từng widget một) ---
  def freeze(self):
    self.canvas.itemconfigure(self._win, state="hidden")

  def thaw(self):
    self.canvas.itemconfigure(self._win, state="normal")
    self._schedule_region()

  # --- Nạp danh sách theo đợt ---
  def clear(self):
    self._cancel_build()
    self._items = []
    self._pos = 0
    for child in self.inner.winfo_children():
      child.destroy()

  def _cancel_build(self):
    if self._build_job is not None:
      self.after_cancel(self._build_job)
      self._build_job = None

  def populate(self, items, build_row):
    """Dựng danh sách; đợt đầu chạy ngay, phần còn lại dựng nền."""
    self.clear()
    self._items = list(items)
    self._build_row = build_row
    self.scroll_top()
    self.freeze()
    self._build_step()

  def _build_step(self):
    self._build_job = None
    self._build_range(min(self._pos + BUILD_CHUNK, len(self._items)))
    self.thaw()
    if self._pos < len(self._items):
      self._build_job = self.after(1, self._build_step)

  def _build_range(self, end):
    while self._pos < end:
      item = self._items[self._pos]
      self._pos += 1
      self._build_row(item)

  def flush(self):
    """Dựng nốt các dòng còn lại (gọi trước khi đọc dữ liệu từ form)."""
    self._cancel_build()
    if self._pos < len(self._items):
      self._build_range(len(self._items))
      self.thaw()

  def append(self, item):
    self.flush()
    self._items.append(item)
    self._build_range(len(self._items))
    self.scroll_to_end()


class StudyPackEditor:

  def __init__(self, root):
    self.root = root
    self.root.title(APP_NAME)
    self.set_initial_geometry()

    self.data = self.empty_pack()
    self.current_path = None
    self.current_topic_index = None
    self.current_question_index = None
    self.mode = "GUI"

    self.theme_mode = DEFAULT_THEME_MODE
    self._effective_theme = None
    self._last_theme_check = 0.0
    self.palette = None
    self._status_job = None

    # Tab nào đang hiển thị đúng dữ liệu của chủ đề hiện tại (nạp lười)
    self._tab_loaded = {
        "notes": False,
        "terms": False,
        "flashcards": False,
        "questions": False,
    }
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []

    self.apply_theme()
    self.create_widgets()
    self.bind_shortcuts()
    self.root.bind("<FocusIn>", self.on_focus_in)
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
    scale = max(self.root.winfo_fpixels("1i") / 96.0, 1.0)
    width = min(int(1300 * scale), self.root.winfo_screenwidth() - 80)
    height = min(int(850 * scale), self.root.winfo_screenheight() - 120)
    self.root.geometry(f"{width}x{height}")

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
    if not HAS_SUNVALLEY:
      return
    try:
      sv_ttk.set_theme(effective)
    except Exception:
      return
    self.palette = PALETTES[effective]
    self.root.configure(background=self.palette["bg"])
    restyle_tree(self.root, self.palette)

  def change_theme(self):
    self.theme_mode = self.theme_var.get()
    self.apply_theme()

  def on_focus_in(self, _event):
    """Theo dõi thay đổi theme của hệ điều hành khi cửa sổ được focus."""
    if self.theme_mode != "system":
      return
    now = time.monotonic()
    if now - self._last_theme_check < 1.0:
      return
    self._last_theme_check = now
    self.apply_theme()

  def new_text(self, parent, **kwargs):
    widget = tk.Text(parent, **kwargs)
    style_classic_widget(widget, self.palette)
    return widget

  def new_listbox(self, parent, **kwargs):
    widget = tk.Listbox(parent, **kwargs)
    style_classic_widget(widget, self.palette)
    return widget

  def new_scroll(self, parent, padding=0):
    frame = ScrollFrame(parent, padding=padding)
    style_classic_widget(frame.canvas, self.palette)
    return frame

  # ------------------------------------------------------------------
  # Status / title / shortcuts
  # ------------------------------------------------------------------
  def set_status(self, message, timeout=4000):
    self.status_var.set(message)
    if self._status_job is not None:
      self.root.after_cancel(self._status_job)
    self._status_job = self.root.after(
        timeout, lambda: self.status_var.set("")
    )

  def update_title(self):
    name = os.path.basename(self.current_path) if self.current_path else None
    self.root.title(f"{name} - {APP_NAME}" if name else APP_NAME)

  def bind_shortcuts(self):
    def make_handler(func):
      def handler(_event):
        func()
        return "break"

      return handler

    bindings = {
        "<Control-n>": self.new_file,
        "<Control-N>": self.new_file,
        "<Control-o>": self.open_file,
        "<Control-O>": self.open_file,
        "<Control-s>": self.save_file,
        "<Control-S>": self.save_file,
        "<Control-Shift-S>": self.save_file_as,
    }
    for sequence, func in bindings.items():
      self.root.bind_all(sequence, make_handler(func))
    # Text có sẵn Ctrl+O (chèn dòng) và Ctrl+N (xuống dòng) chạy trước
    # bind_all, nên phải ghi đè ở mức class.
    self.root.bind_class("Text", "<Control-o>", make_handler(self.open_file))
    self.root.bind_class("Text", "<Control-n>", make_handler(self.new_file))

  # ------------------------------------------------------------------
  # Widgets
  # ------------------------------------------------------------------
  def create_widgets(self):
    self.status_var = tk.StringVar()
    ttk.Label(
        self.root, textvariable=self.status_var, anchor="w", padding=(10, 3)
    ).pack(side=tk.BOTTOM, fill=tk.X)

    menubar = tk.Menu(self.root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(
        label="New Study Pack", command=self.new_file, accelerator="Ctrl+N"
    )
    file_menu.add_command(
        label="Open JSON...", command=self.open_file, accelerator="Ctrl+O"
    )
    file_menu.add_command(
        label="Save JSON", command=self.save_file, accelerator="Ctrl+S"
    )
    file_menu.add_command(
        label="Save JSON As...",
        command=self.save_file_as,
        accelerator="Ctrl+Shift+S",
    )
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)
    menubar.add_cascade(label="File", menu=file_menu)
    self.root.config(menu=menubar)

    main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # --- Cột trái: metadata và danh sách topic ---
    left_frame = ttk.Frame(main_paned, padding=5)
    main_paned.add(left_frame, weight=1)

    meta_frame = ttk.LabelFrame(left_frame, text="General Information", padding=8)
    meta_frame.pack(fill=tk.X, padx=2, pady=2)

    fields = [
        ("Title:", "title"),
        ("Subject:", "subject"),
        ("Level:", "level"),
        ("Language:", "language"),
    ]
    self.meta_entries = {}
    for idx, (label, key) in enumerate(fields):
      ttk.Label(meta_frame, text=label).grid(
          row=idx, column=0, sticky=tk.W, pady=3
      )
      ent = ttk.Entry(meta_frame)
      ent.grid(row=idx, column=1, sticky=tk.EW, pady=3)
      ent.bind(
          "<FocusOut>", lambda e, k=key, entry=ent: self.update_meta(k, entry)
      )
      self.meta_entries[key] = ent
    meta_frame.columnconfigure(1, weight=1)

    topic_frame = ttk.LabelFrame(left_frame, text="Topics", padding=8)
    topic_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=5)

    self.topic_listbox = self.new_listbox(topic_frame, exportselection=False)
    self.topic_listbox.pack(
        side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2
    )
    self.topic_listbox.bind("<<ListboxSelect>>", self.on_select_topic)

    btn_topic_frame = ttk.Frame(topic_frame)
    btn_topic_frame.pack(fill=tk.X, pady=2)
    ttk.Button(btn_topic_frame, text="Add Topic", command=self.add_topic).pack(
        side=tk.LEFT, expand=True, fill=tk.X, padx=1
    )
    ttk.Button(
        btn_topic_frame, text="Delete Topic", command=self.delete_topic
    ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

    # --- Cột phải: Editor và Settings ---
    self.main_notebook = ttk.Notebook(main_paned)
    main_paned.add(self.main_notebook, weight=4)

    self.tab_editor = ttk.Frame(self.main_notebook)
    self.tab_settings = ttk.Frame(self.main_notebook)

    self.main_notebook.add(self.tab_editor, text="Workspace")
    self.main_notebook.add(self.tab_settings, text="Settings")

    self.init_editor_workspace()
    self.init_settings_tab()

  def init_editor_workspace(self):
    mode_toolbar = ttk.Frame(self.tab_editor, padding=2)
    mode_toolbar.pack(fill=tk.X, pady=2)
    ttk.Label(
        mode_toolbar, text="Mode:", font=("Segoe UI", 9, "bold")
    ).pack(side=tk.LEFT, padx=5)
    self.mode_var = tk.StringVar(value="GUI")
    ttk.Radiobutton(
        mode_toolbar,
        text="GUI Form",
        variable=self.mode_var,
        value="GUI",
        command=self.switch_mode,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Radiobutton(
        mode_toolbar,
        text="Plain Text (JSON)",
        variable=self.mode_var,
        value="Text",
        command=self.switch_mode,
    ).pack(side=tk.LEFT, padx=5)

    self.right_container = ttk.Frame(self.tab_editor)
    self.right_container.pack(fill=tk.BOTH, expand=True, pady=2)

    # --- View 1: Plain text ---
    self.text_mode_frame = ttk.Frame(self.right_container)
    self.json_text_widget = self.new_text(
        self.text_mode_frame, wrap=tk.WORD, font=("Consolas", 10)
    )
    self.json_text_widget.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=5)
    ttk.Button(
        self.text_mode_frame,
        text="Apply Changes",
        command=self.apply_plain_text,
    ).pack(anchor=tk.E, pady=2)

    # --- View 2: Form ---
    self.gui_mode_frame = ttk.Frame(self.right_container)

    top_info_frame = ttk.Frame(self.gui_mode_frame)
    top_info_frame.pack(fill=tk.X, pady=2)

    ttk.Label(top_info_frame, text="ID:").grid(
        row=0, column=0, sticky=tk.W, padx=2
    )
    self.t_id_var = tk.StringVar()
    self.t_id_ent = ttk.Entry(
        top_info_frame, textvariable=self.t_id_var, width=10
    )
    self.t_id_ent.grid(row=0, column=1, sticky=tk.W, padx=2)
    self.t_id_ent.bind(
        "<FocusOut>",
        lambda e: self.update_current_topic_field("id", self.t_id_var),
    )

    ttk.Label(top_info_frame, text="Title:").grid(
        row=0, column=2, sticky=tk.W, padx=2
    )
    self.t_title_var = tk.StringVar()
    self.t_title_ent = ttk.Entry(top_info_frame, textvariable=self.t_title_var)
    self.t_title_ent.grid(row=0, column=3, sticky=tk.EW, padx=2)
    self.t_title_ent.bind(
        "<FocusOut>",
        lambda e: self.update_current_topic_field("title", self.t_title_var),
    )
    top_info_frame.columnconfigure(3, weight=1)

    ttk.Label(top_info_frame, text="Summary:").grid(
        row=1, column=0, sticky=tk.W, padx=2, pady=4
    )
    self.t_summary_var = tk.StringVar()
    self.t_summary_ent = ttk.Entry(
        top_info_frame, textvariable=self.t_summary_var
    )
    self.t_summary_ent.grid(
        row=1, column=1, columnspan=3, sticky=tk.EW, padx=2, pady=4
    )
    self.t_summary_ent.bind(
        "<FocusOut>",
        lambda e: self.update_current_topic_field("summary", self.t_summary_var),
    )

    self.topic_notebook = ttk.Notebook(self.gui_mode_frame)
    self.topic_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

    self.tab_notes = ttk.Frame(self.topic_notebook)
    self.tab_terms = ttk.Frame(self.topic_notebook)
    self.tab_flashcards = ttk.Frame(self.topic_notebook)
    self.tab_questions = ttk.Frame(self.topic_notebook)

    self.topic_notebook.add(self.tab_notes, text="Notes")
    self.topic_notebook.add(self.tab_terms, text="Key Terms")
    self.topic_notebook.add(self.tab_flashcards, text="Flashcards")
    self.topic_notebook.add(self.tab_questions, text="Questions")

    self._tab_key_by_widget = {
        str(self.tab_notes): "notes",
        str(self.tab_terms): "terms",
        str(self.tab_flashcards): "flashcards",
        str(self.tab_questions): "questions",
    }
    # Chỉ nạp dữ liệu của tab đang xem; tab khác nạp khi được mở.
    self.topic_notebook.bind(
        "<<NotebookTabChanged>>", lambda e: self.load_visible_tab()
    )

    self.init_notes_gui()
    self.init_terms_gui()
    self.init_flashcards_gui()
    self.init_questions_gui()

    self.switch_mode()

  def init_settings_tab(self):
    settings_frame = ttk.LabelFrame(
        self.tab_settings, text="Appearance", padding=15
    )
    settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ttk.Label(settings_frame, text="Theme Mode:").pack(
        anchor=tk.W, pady=5
    )

    self.theme_var = tk.StringVar(value=self.theme_mode)
    state = tk.NORMAL if HAS_SUNVALLEY else tk.DISABLED
    for text, value in (
        ("Light", "light"),
        ("Dark", "dark"),
        ("System (Auto)", "system"),
    ):
      ttk.Radiobutton(
          settings_frame,
          text=text,
          variable=self.theme_var,
          value=value,
          command=self.change_theme,
          state=state,
      ).pack(anchor=tk.W, pady=3)

    if not HAS_SUNVALLEY:
      ttk.Label(
          settings_frame,
          text="Warning: 'sv-ttk' package is not installed.",
          foreground="red",
      ).pack(anchor=tk.W, pady=10)

  # ------------------------------------------------------------------
  # Mode, commit, file operations
  # ------------------------------------------------------------------
  def render_json_text(self):
    self.json_text_widget.delete("1.0", tk.END)
    self.json_text_widget.insert(
        tk.END, json.dumps(self.data, ensure_ascii=False, indent=2)
    )
    self.json_text_widget.edit_modified(False)

  def switch_mode(self):
    new_mode = self.mode_var.get()
    if new_mode == "Text":
      if self.mode == "GUI":
        self.commit_meta()
        self.commit_current_topic()
      self.mode = new_mode
      self.gui_mode_frame.pack_forget()
      self.text_mode_frame.pack(fill=tk.BOTH, expand=True)
      self.render_json_text()
    else:
      self.mode = new_mode
      self.text_mode_frame.pack_forget()
      self.gui_mode_frame.pack(fill=tk.BOTH, expand=True)
      self.load_topic_gui_data()

  def parse_pack_text(self, raw):
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError as e:
      messagebox.showerror("JSON Error", f"Invalid syntax: {e}")
      return None
    if not isinstance(parsed, dict):
      messagebox.showerror("JSON Error", "A study pack must be a JSON object.")
      return None
    parsed.setdefault("topics", [])
    return parsed

  def apply_plain_text(self):
    parsed = self.parse_pack_text(self.json_text_widget.get("1.0", tk.END))
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
      if self.json_text_widget.edit_modified():
        parsed = self.parse_pack_text(self.json_text_widget.get("1.0", tk.END))
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
      value = ent.get()
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
    for field, var in (
        ("id", self.t_id_var),
        ("title", self.t_title_var),
        ("summary", self.t_summary_var),
    ):
      value = var.get()
      if t.get(field, "") != value:
        t[field] = value
        label_changed = label_changed or field in ("id", "title")
    if label_changed:
      self.refresh_topic_listbox_item()

    if self._tab_loaded["notes"]:
      t["notes"] = self.collect_notes()
    if self._tab_loaded["terms"]:
      t["key_terms"] = self.collect_terms()
    if self._tab_loaded["flashcards"]:
      t["flashcards"] = self.collect_flashcards()
    if self._tab_loaded["questions"]:
      self.save_current_question_form(silent=True)

  def new_file(self):
    if messagebox.askyesno(
        "Confirm", "Discard unsaved changes?"
    ):
      self.data = self.empty_pack()
      self.current_path = None
      self.refresh_ui()
      self.update_title()

  def open_file(self):
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not file_path:
      return
    try:
      with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
      if not isinstance(data, dict):
        raise ValueError("A study pack must be a JSON object.")
    except Exception as e:
      messagebox.showerror("Error", f"Failed to read file:\n{e}")
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
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if file_path:
      self.write_file(file_path)

  def write_file(self, file_path):
    tmp_path = file_path + ".tmp"
    try:
      with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(self.data, f, ensure_ascii=False, indent=2)
      os.replace(tmp_path, file_path)  # ghi nguyên tử, tránh hỏng file
    except Exception as e:
      messagebox.showerror("Error", f"Failed to save file:\n{e}")
      return
    self.current_path = file_path
    self.update_title()
    self.set_status(f"File saved: {os.path.basename(file_path)}")

  # ------------------------------------------------------------------
  # Metadata và danh sách topic
  # ------------------------------------------------------------------
  def update_meta(self, key, entry):
    value = entry.get()
    if value != str(self.data.get(key, "")):
      self.data[key] = value

  @staticmethod
  def topic_label(t):
    return f"{t.get('id', '')}: {t.get('title', 'Untitled')}"

  def refresh_topic_list(self):
    self.topic_listbox.delete(0, tk.END)
    labels = [self.topic_label(t) for t in self.data.get("topics", [])]
    if labels:
      self.topic_listbox.insert(tk.END, *labels)

  def refresh_topic_listbox_item(self):
    idx = self.current_topic_index
    if idx is None:
      return
    replace_listbox_item(
        self.topic_listbox, idx, self.topic_label(self.data["topics"][idx])
    )

  def invalidate_tabs(self):
    for key in self._tab_loaded:
      self._tab_loaded[key] = False
    self.current_question_index = None

  def reset_topic_view(self):
    """Xóa trạng thái chủ đề đang mở (khi đổi dữ liệu hoặc xóa topic)."""
    self.current_topic_index = None
    self.invalidate_tabs()
    for var in (self.t_id_var, self.t_title_var, self.t_summary_var):
      var.set("")
    self.note_widgets = []
    self.term_widgets = []
    self.fc_widgets = []
    self.notes_view.clear()
    self.terms_view.clear()
    self.fc_view.clear()
    self.q_listbox.delete(0, tk.END)
    self.q_detail.clear()

  def refresh_ui(self):
    self.reset_topic_view()
    for key, ent in self.meta_entries.items():
      ent.delete(0, tk.END)
      ent.insert(0, str(self.data.get(key, "")))
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
    self.topic_listbox.insert(tk.END, self.topic_label(new_t))
    self.topic_listbox.selection_clear(0, tk.END)
    self.topic_listbox.selection_set(idx)
    self.topic_listbox.see(idx)
    self.on_select_topic()
    if self.mode == "Text":
      self.render_json_text()

  def delete_topic(self):
    selected = self.topic_listbox.curselection()
    if not selected:
      return
    del self.data["topics"][selected[0]]
    self.reset_topic_view()
    self.refresh_topic_list()
    if self.mode == "Text":
      self.render_json_text()

  def on_select_topic(self, _event=None):
    selected = self.topic_listbox.curselection()
    if not selected:
      return
    idx = selected[0]
    if idx == self.current_topic_index:
      return
    self.commit_current_topic()  # lưu form của topic trước khi chuyển
    self.current_topic_index = idx
    self.invalidate_tabs()
    if self.mode == "GUI":
      self.load_topic_gui_data()

  def update_current_topic_field(self, field, var):
    idx = self.current_topic_index
    if idx is None:
      return
    t = self.data["topics"][idx]
    value = var.get()
    if t.get(field, "") == value:
      return
    t[field] = value
    if field in ("id", "title"):
      self.refresh_topic_listbox_item()

  def load_topic_gui_data(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    self.t_id_var.set(t.get("id", ""))
    self.t_title_var.set(t.get("title", ""))
    self.t_summary_var.set(t.get("summary", ""))
    self.load_visible_tab()

  def load_visible_tab(self):
    """Nạp dữ liệu cho tab đang xem nếu chưa nạp."""
    if self.current_topic_index is None or self.mode != "GUI":
      return
    key = self._tab_key_by_widget.get(self.topic_notebook.select())
    if key is None or self._tab_loaded[key]:
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
  # 1. Notes
  # ------------------------------------------------------------------
  def init_notes_gui(self):
    top_ctrl = ttk.Frame(self.tab_notes, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(
        top_ctrl, text="+ Add Section", command=self.add_note_section
    ).pack(side=tk.LEFT)
    ttk.Button(
        top_ctrl, text="Save Notes", command=self.save_notes_form
    ).pack(side=tk.RIGHT)

    self.notes_view = self.new_scroll(self.tab_notes)
    self.notes_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

  def load_notes_ui(self, notes_list):
    self.note_widgets = []
    self.notes_view.populate(notes_list, self.build_note_section)

  def build_note_section(self, sec):
    sec_frame = ttk.LabelFrame(
        self.notes_view.inner,
        text=f"Section {len(self.note_widgets) + 1}",
        padding=8,
    )
    sec_frame.pack(fill=tk.X, expand=True, padx=2, pady=5)

    h_frame = ttk.Frame(sec_frame)
    h_frame.pack(fill=tk.X, expand=True, pady=2)
    ttk.Label(h_frame, text="Heading:").pack(side=tk.LEFT)
    h_ent = ttk.Entry(h_frame)
    h_ent.insert(0, sec.get("heading", ""))
    h_ent.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    ttk.Button(
        h_frame,
        text="Delete",
        command=lambda f=sec_frame: self.remove_note_section(f),
    ).pack(side=tk.RIGHT)

    p_frame = ttk.Frame(sec_frame)
    p_frame.pack(fill=tk.X, expand=True, pady=2)
    ttk.Label(p_frame, text="Points:").pack(
        anchor=tk.W
    )
    p_txt = self.new_text(p_frame, height=4, wrap=tk.WORD)
    p_txt.insert("1.0", "\n".join(sec.get("points", [])))
    p_txt.pack(fill=tk.X, expand=True, pady=2)
    self.note_widgets.append((h_ent, p_txt, sec_frame))

  def add_note_section(self):
    if self.current_topic_index is None:
      return
    self.notes_view.append(
        {"heading": "New Section", "points": ["Point about **term**."]}
    )

  def remove_note_section(self, sec_frame):
    self.note_widgets = [w for w in self.note_widgets if w[2] is not sec_frame]
    sec_frame.destroy()

  def collect_notes(self):
    self.notes_view.flush()
    notes = []
    for h_ent, p_txt, _ in self.note_widgets:
      points = [
          pt.strip()
          for pt in p_txt.get("1.0", tk.END).splitlines()
          if pt.strip()
      ]
      notes.append({"heading": h_ent.get(), "points": points})
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
    top_ctrl = ttk.Frame(self.tab_terms, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(top_ctrl, text="+ Add Term", command=self.add_term_row).pack(
        side=tk.LEFT
    )
    ttk.Button(
        top_ctrl, text="Save Terms", command=self.save_terms_form
    ).pack(side=tk.RIGHT)

    self.terms_view = self.new_scroll(self.tab_terms)
    self.terms_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

  def load_terms_ui(self, terms_list):
    self.term_widgets = []
    self.terms_view.populate(terms_list, self.build_term_row)

  def build_term_row(self, item):
    row_f = ttk.Frame(self.terms_view.inner, padding=2)
    row_f.pack(fill=tk.X, expand=True, pady=2)
    ttk.Label(
        row_f, text=f"Term {len(self.term_widgets) + 1}:", width=8
    ).pack(side=tk.LEFT)
    t_ent = ttk.Entry(row_f, width=22)
    t_ent.insert(0, item.get("term", ""))
    t_ent.pack(side=tk.LEFT, padx=2)

    ttk.Label(row_f, text="Def:", width=4).pack(side=tk.LEFT)
    d_ent = ttk.Entry(row_f)
    d_ent.insert(0, item.get("definition", ""))
    d_ent.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
    ttk.Button(
        row_f,
        text="X",
        width=3,
        command=lambda f=row_f: self.remove_term_row(f),
    ).pack(side=tk.RIGHT, padx=2)
    self.term_widgets.append((t_ent, d_ent, row_f))

  def add_term_row(self):
    if self.current_topic_index is None:
      return
    self.terms_view.append({"term": "New Term", "definition": "Definition here."})

  def remove_term_row(self, row_f):
    self.term_widgets = [w for w in self.term_widgets if w[2] is not row_f]
    row_f.destroy()

  def collect_terms(self):
    self.terms_view.flush()
    return [
        {"term": t_ent.get(), "definition": d_ent.get()}
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
    top_ctrl = ttk.Frame(self.tab_flashcards, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(
        top_ctrl, text="+ Add Flashcard", command=self.add_fc_row
    ).pack(side=tk.LEFT)
    ttk.Button(
        top_ctrl, text="Save Flashcards", command=self.save_fc_form
    ).pack(side=tk.RIGHT)

    self.fc_view = self.new_scroll(self.tab_flashcards)
    self.fc_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

  def load_flashcards_ui(self, fc_list):
    self.fc_widgets = []
    self.fc_view.populate(fc_list, self.build_fc_row)

  def build_fc_row(self, fc):
    row_f = ttk.LabelFrame(
        self.fc_view.inner,
        text=f"Flashcard {len(self.fc_widgets) + 1}",
        padding=8,
    )
    row_f.pack(fill=tk.X, expand=True, padx=2, pady=4)

    f_frame = ttk.Frame(row_f)
    f_frame.pack(fill=tk.X, expand=True, pady=2)
    ttk.Label(f_frame, text="Front:", width=20).pack(
        side=tk.LEFT
    )
    f_ent = ttk.Entry(f_frame)
    f_ent.insert(0, fc.get("front", ""))
    f_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    b_frame = ttk.Frame(row_f)
    b_frame.pack(fill=tk.X, expand=True, pady=2)
    ttk.Label(b_frame, text="Back:", width=20).pack(
        side=tk.LEFT
    )
    b_ent = ttk.Entry(b_frame)
    b_ent.insert(0, fc.get("back", ""))
    b_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    ttk.Button(
        row_f,
        text="Delete",
        command=lambda f=row_f: self.remove_fc_row(f),
    ).pack(anchor=tk.E, pady=2)
    self.fc_widgets.append((f_ent, b_ent, row_f))

  def add_fc_row(self):
    if self.current_topic_index is None:
      return
    self.fc_view.append({"front": "Question?", "back": "Answer."})

  def remove_fc_row(self, row_f):
    self.fc_widgets = [w for w in self.fc_widgets if w[2] is not row_f]
    row_f.destroy()

  def collect_flashcards(self):
    self.fc_view.flush()
    return [
        {"front": f_ent.get(), "back": b_ent.get()}
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
    q_paned = ttk.PanedWindow(self.tab_questions, orient=tk.HORIZONTAL)
    q_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    left_q_frame = ttk.Frame(q_paned, padding=5)
    q_paned.add(left_q_frame, weight=1)

    ttk.Label(
        left_q_frame, text="Questions List", font=("Segoe UI", 9, "bold")
    ).pack(anchor=tk.W, pady=2)

    self.q_listbox = self.new_listbox(left_q_frame, exportselection=False)
    self.q_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
    self.q_listbox.bind("<<ListboxSelect>>", self.on_select_question_item)

    q_ctrl_frame = ttk.Frame(left_q_frame)
    q_ctrl_frame.pack(fill=tk.X, pady=2)
    self.q_type_combo = ttk.Combobox(
        q_ctrl_frame,
        values=["mcq", "truefalse", "short", "cloze", "match", "tfs"],
        state="readonly",
        width=10,
    )
    self.q_type_combo.set("mcq")
    self.q_type_combo.pack(side=tk.LEFT, padx=1)
    ttk.Button(
        q_ctrl_frame, text="+ Add", command=self.add_single_question
    ).pack(side=tk.LEFT, padx=1)
    ttk.Button(
        q_ctrl_frame, text="Delete", command=self.delete_single_question
    ).pack(side=tk.LEFT, padx=1)

    right_q_frame = ttk.Frame(q_paned, padding=5)
    q_paned.add(right_q_frame, weight=3)

    # Nút lưu đặt trước (side=bottom) để luôn hiển thị
    save_q_btn_frame = ttk.Frame(right_q_frame)
    save_q_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
    ttk.Button(
        save_q_btn_frame,
        text="Save Question Changes",
        command=lambda: self.save_current_question_form(),
    ).pack(side=tk.RIGHT)

    self.q_detail = self.new_scroll(right_q_frame, padding=5)
    self.q_detail.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    self.q_detail_container = self.q_detail.inner

  @staticmethod
  def question_label(idx, q):
    prompt = str(q.get("prompt", ""))
    snippet = prompt[:35] + ("..." if len(prompt) > 35 else "")
    return f"Q{idx + 1} [{q.get('type', 'mcq')}]: {snippet}"

  def load_questions_list(self):
    self.q_listbox.delete(0, tk.END)
    self.current_question_index = None
    self.q_detail.clear()
    if self.current_topic_index is None:
      return
    questions = self.data["topics"][self.current_topic_index].get(
        "questions", []
    )
    labels = [self.question_label(i, q) for i, q in enumerate(questions)]
    if labels:
      self.q_listbox.insert(tk.END, *labels)

  def on_select_question_item(self, _event=None):
    selected = self.q_listbox.curselection()
    if not selected:
      return
    idx = selected[0]
    if idx == self.current_question_index:
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
      self.build_question_form(questions[self.current_question_index])
    finally:
      self.q_detail.thaw()

  def build_question_form(self, q):
    container = self.q_detail_container
    q_type = q.get("type", "mcq")

    ttk.Label(
        container,
        text=f"Editing Question {self.current_question_index + 1} [{q_type.upper()}]",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor=tk.W, pady=5)

    p_box = ttk.Frame(container)
    p_box.pack(fill=tk.X, pady=3)
    ttk.Label(p_box, text="Prompt:", width=12).pack(side=tk.LEFT)
    self.det_prompt_ent = ttk.Entry(p_box)
    self.det_prompt_ent.insert(0, q.get("prompt", ""))
    self.det_prompt_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    self.det_spec = {"type": q_type}

    if q_type == "mcq":
      ctx_box = ttk.Frame(container)
      ctx_box.pack(fill=tk.X, pady=2)
      ttk.Label(ctx_box, text="Context:", width=12).pack(side=tk.LEFT)
      self.det_mcq_context = ttk.Entry(ctx_box)
      self.det_mcq_context.insert(0, q.get("context", ""))
      self.det_mcq_context.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      src_box = ttk.Frame(container)
      src_box.pack(fill=tk.X, pady=2)
      ttk.Label(src_box, text="Source:", width=12).pack(side=tk.LEFT)
      self.det_mcq_source = ttk.Entry(src_box)
      self.det_mcq_source.insert(0, q.get("source", ""))
      self.det_mcq_source.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      opts = q.get("options", ["", "", "", ""])
      self.det_spec["opt_ents"] = []
      for o_idx, opt_text in enumerate(opts):
        o_box = ttk.Frame(container)
        o_box.pack(fill=tk.X, pady=2)
        ttk.Label(o_box, text=f"Option {o_idx}:", width=12).pack(side=tk.LEFT)
        o_ent = ttk.Entry(o_box)
        o_ent.insert(0, opt_text)
        o_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.det_spec["opt_ents"].append(o_ent)

      ans_box = ttk.Frame(container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Correct Index:", width=18).pack(
          side=tk.LEFT
      )
      self.det_ans_spin = ttk.Spinbox(
          ans_box, from_=0, to=max(3, len(opts) - 1), width=5
      )
      self.det_ans_spin.set(q.get("answer", 0))
      self.det_ans_spin.pack(side=tk.LEFT, padx=2)

    elif q_type == "truefalse":
      ans_box = ttk.Frame(container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Answer:", width=12).pack(side=tk.LEFT)
      self.det_tf_var = tk.StringVar(value=str(q.get("answer", True)))
      ttk.Radiobutton(
          ans_box, text="True", variable=self.det_tf_var, value="True"
      ).pack(side=tk.LEFT, padx=5)
      ttk.Radiobutton(
          ans_box, text="False", variable=self.det_tf_var, value="False"
      ).pack(side=tk.LEFT, padx=5)

    elif q_type == "short":
      ans_box = ttk.Frame(container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Model Answer:", width=15).pack(side=tk.LEFT)
      self.det_short_ent = ttk.Entry(ans_box)
      self.det_short_ent.insert(0, q.get("answer", ""))
      self.det_short_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    elif q_type == "cloze":
      ans_box = ttk.Frame(container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Answers:", width=18).pack(side=tk.LEFT)
      self.det_cloze_ent = ttk.Entry(ans_box)
      ans_list = q.get("answers", [])
      self.det_cloze_ent.insert(
          0,
          ", ".join(ans_list) if isinstance(ans_list, list) else str(ans_list),
      )
      self.det_cloze_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    elif q_type == "match":
      pairs = q.get("pairs", [])
      self.det_spec["pair_ents"] = []
      pf_box = ttk.LabelFrame(container, text="Pairs (Left : Right)", padding=5)
      pf_box.pack(fill=tk.X, pady=3)
      for p_obj in pairs:
        pr_f = ttk.Frame(pf_box)
        pr_f.pack(fill=tk.X, pady=2)
        l_ent = ttk.Entry(pr_f, width=20)
        l_ent.insert(0, p_obj.get("left", ""))
        l_ent.pack(side=tk.LEFT, padx=2)
        ttk.Label(pr_f, text="->").pack(side=tk.LEFT)
        r_ent = ttk.Entry(pr_f)
        r_ent.insert(0, p_obj.get("right", ""))
        r_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.det_spec["pair_ents"].append((l_ent, r_ent))

    elif q_type == "tfs":
      q_box = ttk.Frame(container)
      q_box.pack(fill=tk.X, pady=3)
      ttk.Label(q_box, text="Quote:", width=10).pack(side=tk.LEFT)
      self.det_quote_ent = ttk.Entry(q_box)
      self.det_quote_ent.insert(0, q.get("quote", ""))
      self.det_quote_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      src_tfs_box = ttk.Frame(container)
      src_tfs_box.pack(fill=tk.X, pady=3)
      ttk.Label(src_tfs_box, text="Source:", width=10).pack(side=tk.LEFT)
      self.det_tfs_source = ttk.Entry(src_tfs_box)
      self.det_tfs_source.insert(0, q.get("source", ""))
      self.det_tfs_source.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      items = q.get("items", [])
      self.det_spec["tfs_item_ents"] = []
      tfs_box = ttk.LabelFrame(
          container, text="Statements & Answers", padding=5
      )
      tfs_box.pack(fill=tk.X, pady=3)
      for itm in items:
        it_f = ttk.Frame(tfs_box)
        it_f.pack(fill=tk.X, pady=2)
        txt_ent = ttk.Entry(it_f)
        txt_ent.insert(0, itm.get("text", ""))
        txt_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ans_var = tk.StringVar(value=str(itm.get("answer", True)))
        ttk.Radiobutton(it_f, text="T", variable=ans_var, value="True").pack(
            side=tk.LEFT
        )
        ttk.Radiobutton(it_f, text="F", variable=ans_var, value="False").pack(
            side=tk.LEFT
        )
        self.det_spec["tfs_item_ents"].append((txt_ent, ans_var))

    exp_box = ttk.Frame(container)
    exp_box.pack(fill=tk.X, pady=3)
    ttk.Label(exp_box, text="Explanation:", width=12).pack(side=tk.LEFT)
    self.det_exp_ent = ttk.Entry(exp_box)
    self.det_exp_ent.insert(0, q.get("explanation", ""))
    self.det_exp_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

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

    q["prompt"] = self.det_prompt_ent.get()
    q["explanation"] = self.det_exp_ent.get()

    if q_type == "mcq":
      q["options"] = [ent.get() for ent in self.det_spec["opt_ents"]]
      try:
        q["answer"] = int(self.det_ans_spin.get())
      except ValueError:
        q["answer"] = 0
      self.set_or_remove(q, "context", self.det_mcq_context.get())
      self.set_or_remove(q, "source", self.det_mcq_source.get())
    elif q_type == "truefalse":
      q["answer"] = self.det_tf_var.get() == "True"
    elif q_type == "short":
      q["answer"] = self.det_short_ent.get()
    elif q_type == "cloze":
      ans_str = self.det_cloze_ent.get()
      q["answers"] = [a.strip() for a in ans_str.split(",") if a.strip()]
    elif q_type == "match":
      q["pairs"] = [
          {"left": l_ent.get(), "right": r_ent.get()}
          for l_ent, r_ent in self.det_spec["pair_ents"]
      ]
    elif q_type == "tfs":
      q["quote"] = self.det_quote_ent.get()
      self.set_or_remove(q, "source", self.det_tfs_source.get())
      q["items"] = [
          {"text": txt_ent.get(), "answer": ans_var.get() == "True"}
          for txt_ent, ans_var in self.det_spec["tfs_item_ents"]
      ]

    idx = self.current_question_index
    replace_listbox_item(self.q_listbox, idx, self.question_label(idx, q))

    if not silent:
      self.set_status("Question updated.")

  def add_single_question(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    questions = t.setdefault("questions", [])

    q_type = self.q_type_combo.get()
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
    self.q_listbox.insert(tk.END, self.question_label(idx, new_q))
    self.q_listbox.selection_clear(0, tk.END)
    self.q_listbox.selection_set(idx)
    self.q_listbox.see(idx)
    self.on_select_question_item()

  def delete_single_question(self):
    selected = self.q_listbox.curselection()
    if not selected or self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    del t["questions"][selected[0]]
    self.load_questions_list()


if __name__ == "__main__":
  if ENABLE_DPI_AWARENESS:
    enable_dpi_awareness()
  root = tk.Tk()
  root.withdraw()  # dựng xong mới hiện, tránh nháy cửa sổ nửa vời lúc khởi động
  app = StudyPackEditor(root)
  root.update_idletasks()
  root.deiconify()
  root.mainloop()
