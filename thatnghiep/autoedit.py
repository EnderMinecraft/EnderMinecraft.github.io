import json
import platform
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HAS_SUNVALLEY = False
try:
  import sv_ttk

  HAS_SUNVALLEY = True
except ImportError:
  HAS_SUNVALLEY = False


class StudyPackEditor:

  def __init__(self, root):
    self.root = root
    self.root.title("Study Pack Editor")
    self.root.geometry("1300x850")

    self.bind_global_shortcuts()

    self.current_theme = "light"
    self.apply_theme("light")

    self.data = {
        "format": "studypack",
        "version": 1,
        "title": "",
        "subject": "",
        "level": "",
        "language": "en",
        "topics": [],
    }

    self.current_topic_index = None
    self.current_question_index = None
    self.mode = "GUI"

    self.create_widgets()

  def bind_global_shortcuts(self):
    self.root.bind_all("<Control-o>", lambda e: self.open_file())
    self.root.bind_all("<Control-s>", lambda e: self.save_file())

  def get_system_theme(self):
    if platform.system() == "Windows":
      try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "dark" if value == 0 else "light"
      except Exception:
        pass
    return "light"

  def apply_theme(self, mode):
    if not HAS_SUNVALLEY:
      return

    target_theme = self.get_system_theme() if mode == "system" else mode
    try:
      self.root.attributes("-alpha", 0.0)
    except Exception:
      pass

    sv_ttk.set_theme(target_theme)
    self.current_theme = mode

    def restore_alpha():
      try:
        self.root.attributes("-alpha", 1.0)
      except Exception:
        pass

    self.root.after(40, restore_alpha)

  def create_widgets(self):
    menubar = tk.Menu(self.root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(
        label="New Study Pack", command=self.new_file, accelerator="Ctrl+N"
    )
    file_menu.add_command(
        label="Open JSON...", command=self.open_file, accelerator="Ctrl+O"
    )
    file_menu.add_command(
        label="Save JSON...", command=self.save_file, accelerator="Ctrl+S"
    )
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)
    menubar.add_cascade(label="File", menu=file_menu)
    self.root.config(menu=menubar)

    main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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

    self.topic_listbox = tk.Listbox(topic_frame, exportselection=False)
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

    self.main_notebook = ttk.Notebook(main_paned)
    main_paned.add(self.main_notebook, weight=4)

    self.tab_editor = ttk.Frame(self.main_notebook)
    self.tab_settings = ttk.Frame(self.main_notebook)

    self.main_notebook.add(self.tab_editor, text="Workspace")
    self.main_notebook.add(self.tab_settings, text="Settings")

    self.init_editor_workspace()
    self.init_settings_tab()

  def init_settings_tab(self):
    settings_frame = ttk.LabelFrame(
        self.tab_settings, text="Appearance", padding=15
    )
    settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ttk.Label(settings_frame, text="Theme Mode:").pack(anchor=tk.W, pady=5)

    self.theme_var = tk.StringVar(value="light")

    ttk.Radiobutton(
        settings_frame,
        text="Light",
        variable=self.theme_var,
        value="light",
        command=lambda: self.apply_theme("light"),
    ).pack(anchor=tk.W, pady=3)
    ttk.Radiobutton(
        settings_frame,
        text="Dark",
        variable=self.theme_var,
        value="dark",
        command=lambda: self.apply_theme("dark"),
    ).pack(anchor=tk.W, pady=3)
    ttk.Radiobutton(
        settings_frame,
        text="System (Auto)",
        variable=self.theme_var,
        value="system",
        command=lambda: self.apply_theme("system"),
    ).pack(anchor=tk.W, pady=3)

    if not HAS_SUNVALLEY:
      ttk.Label(
          settings_frame,
          text="Warning: 'sv-ttk' package is not installed.",
          foreground="red",
      ).pack(anchor=tk.W, pady=10)

  def init_editor_workspace(self):
    mode_toolbar = ttk.Frame(self.tab_editor, padding=2)
    mode_toolbar.pack(fill=tk.X, pady=2)
    ttk.Label(mode_toolbar, text="Mode:", font=("Segoe UI", 9, "bold")).pack(
        side=tk.LEFT, padx=5
    )

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

    self.text_mode_frame = ttk.Frame(self.right_container)
    self.json_text_widget = tk.Text(
        self.text_mode_frame, wrap=tk.WORD, font=("Consolas", 10)
    )
    self.json_text_widget.pack(
        fill=tk.BOTH, expand=True, side=tk.TOP, pady=5
    )
    ttk.Button(
        self.text_mode_frame,
        text="Apply Changes",
        command=self.apply_plain_text,
    ).pack(anchor=tk.E, pady=2)

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

    self.init_notes_gui()
    self.init_terms_gui()
    self.init_flashcards_gui()
    self.init_questions_gui_optimized()

    self.switch_mode()

  # --- HÀM TỰ ĐỘNG ĐỒNG BỘ DỮ LIỆU TẤT CẢ CÁC FORM ---
  def sync_current_forms(self):
    if self.current_topic_index is None:
      return
    try:
      self.save_notes_form(silent=True)
    except Exception:
      pass
    try:
      self.save_terms_form(silent=True)
    except Exception:
      pass
    try:
      self.save_fc_form(silent=True)
    except Exception:
      pass
    try:
      self.save_current_question_form(silent=True)
    except Exception:
      pass

  def switch_mode(self):
    if self.mode == "GUI":
      self.sync_current_forms()

    self.mode = self.mode_var.get()
    if self.mode == "Text":
      self.gui_mode_frame.pack_forget()
      self.text_mode_frame.pack(fill=tk.BOTH, expand=True)
      formatted_json = json.dumps(self.data, ensure_ascii=False, indent=2)
      self.json_text_widget.delete("1.0", tk.END)
      self.json_text_widget.insert(tk.END, formatted_json)
    else:
      self.text_mode_frame.pack_forget()
      self.gui_mode_frame.pack(fill=tk.BOTH, expand=True)
      if self.current_topic_index is not None:
        self.load_topic_gui_data()

  def apply_plain_text(self):
    raw_text = self.json_text_widget.get("1.0", tk.END).strip()
    try:
      parsed = json.loads(raw_text)
      self.data = parsed
      self.refresh_ui()
      messagebox.showinfo("Success", "Changes applied successfully.")
    except json.JSONDecodeError as e:
      messagebox.showerror("JSON Error", f"Invalid syntax: {e}")

  def new_file(self):
    if messagebox.askyesno("Confirm", "Discard unsaved changes?"):
      self.data = {
          "format": "studypack",
          "version": 1,
          "title": "",
          "subject": "",
          "level": "",
          "language": "en",
          "topics": [],
      }
      self.refresh_ui()

  def open_file(self):
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file_path:
      try:
        with open(file_path, "r", encoding="utf-8") as f:
          self.data = json.load(f)
        self.refresh_ui()
        messagebox.showinfo("Success", "File loaded successfully.")
      except Exception as e:
        messagebox.showerror("Error", f"Failed to read file:\n{e}")

  def save_file(self):
    # Tự động đồng bộ toàn bộ dữ liệu form hiện tại trước khi lưu tệp
    if self.mode == "GUI":
      self.sync_current_forms()

    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if file_path:
      try:
        with open(file_path, "w", encoding="utf-8") as f:
          json.dump(self.data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Success", "File saved successfully.")
      except Exception as e:
        messagebox.showerror("Error", f"Failed to save file:\n{e}")

  def update_meta(self, key, entry):
    self.data[key] = entry.get()

  def refresh_ui(self):
    for key, ent in self.meta_entries.items():
      ent.delete(0, tk.END)
      ent.insert(0, str(self.data.get(key, "")))

    self.topic_listbox.delete(0, tk.END)
    for t in self.data.get("topics", []):
      self.topic_listbox.insert(
          tk.END, f"{t.get('id', '')}: {t.get('title', 'Untitled')}"
      )

    self.current_topic_index = None
    if self.mode == "Text":
      self.json_text_widget.delete("1.0", tk.END)
      self.json_text_widget.insert(
          tk.END, json.dumps(self.data, ensure_ascii=False, indent=2)
      )

  def add_topic(self):
    new_id = f"t{len(self.data['topics']) + 1}"
    new_t = {
        "id": new_id,
        "title": "New Topic",
        "summary": "",
        "notes": [],
        "key_terms": [],
        "flashcards": [],
        "questions": [],
    }
    self.data["topics"].append(new_t)
    self.refresh_ui()
    self.topic_listbox.selection_set(len(self.data["topics"]) - 1)
    self.on_select_topic(None)

  def delete_topic(self):
    selected = self.topic_listbox.curselection()
    if not selected:
      return
    idx = selected[0]
    del self.data["topics"][idx]
    self.refresh_ui()

  def on_select_topic(self, event):
    # Tự động đồng bộ form của chủ đề cũ trước khi chuyển sang chủ đề mới
    if self.mode == "GUI":
      self.sync_current_forms()

    selected = self.topic_listbox.curselection()
    if not selected:
      return
    self.current_topic_index = selected[0]
    if self.mode == "GUI":
      self.load_topic_gui_data()

  def update_current_topic_field(self, field, var):
    if self.current_topic_index is not None:
      self.data["topics"][self.current_topic_index][field] = var.get()
      self.refresh_topic_listbox_item()

  def refresh_topic_listbox_item(self):
    if self.current_topic_index is not None:
      t = self.data["topics"][self.current_topic_index]
      self.topic_listbox.delete(self.current_topic_index)
      self.topic_listbox.insert(
          self.current_topic_index,
          f"{t.get('id', '')}: {t.get('title', 'Untitled')}",
      )
      self.topic_listbox.selection_set(self.current_topic_index)

  def load_topic_gui_data(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    self.t_id_var.set(t.get("id", ""))
    self.t_title_var.set(t.get("title", ""))
    self.t_summary_var.set(t.get("summary", ""))

    self.load_notes_ui(t.get("notes", []))
    self.load_terms_ui(t.get("key_terms", []))
    self.load_flashcards_ui(t.get("flashcards", []))
    self.load_questions_list_optimized()

  def bind_responsive_canvas(self, canvas, window_id):
    canvas._last_w = 0

    def on_resize(event):
      if event.width > 1 and event.width != canvas._last_w:
        canvas._last_w = event.width
        canvas.itemconfig(window_id, width=event.width)

    canvas.bind("<Configure>", on_resize)

  def init_notes_gui(self):
    top_ctrl = ttk.Frame(self.tab_notes, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(
        top_ctrl, text="+ Add Section", command=self.add_note_section
    ).pack(side=tk.LEFT)
    ttk.Button(
        top_ctrl, text="Save Notes", command=lambda: self.save_notes_form(False)
    ).pack(side=tk.RIGHT)

    self.notes_canvas = tk.Canvas(self.tab_notes, highlightthickness=0)
    self.notes_scroll = ttk.Scrollbar(
        self.tab_notes, orient="vertical", command=self.notes_canvas.yview
    )
    self.notes_container = ttk.Frame(self.notes_canvas)
    self.notes_window_id = self.notes_canvas.create_window(
        (0, 0), window=self.notes_container, anchor="nw"
    )

    self.notes_container.bind(
        "<Configure>",
        lambda e: self.notes_canvas.configure(
            scrollregion=self.notes_canvas.bbox("all")
        ),
    )
    self.bind_responsive_canvas(self.notes_canvas, self.notes_window_id)
    self.notes_canvas.configure(yscrollcommand=self.notes_scroll.set)
    self.notes_canvas.pack(
        side="left", fill="both", expand=True, padx=5, pady=5
    )
    self.notes_scroll.pack(side="right", fill="y")
    self.note_section_widgets = []

  def load_notes_ui(self, notes_list):
    for widget in self.notes_container.winfo_children():
      widget.destroy()
    self.note_section_widgets = []
    for s_idx, sec in enumerate(notes_list):
      sec_frame = ttk.LabelFrame(
          self.notes_container, text=f"Section {s_idx+1}", padding=8
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
      ttk.Label(p_frame, text="Points:").pack(anchor=tk.W)
      p_txt = tk.Text(p_frame, height=4, wrap=tk.WORD)
      points_text = "\n".join(sec.get("points", []))
      p_txt.insert("1.0", points_text)
      p_txt.pack(fill=tk.X, expand=True, pady=2)
      self.note_section_widgets.append((h_ent, p_txt, sec_frame))

  def add_note_section(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    if "notes" not in t:
      t["notes"] = []
    t["notes"].append({"heading": "New Section", "points": ["Point about **term**."] })
    self.load_notes_ui(t["notes"])

  def remove_note_section(self, sec_frame):
    for i, (h, p, f) in enumerate(self.note_section_widgets):
      if f == sec_frame:
        del self.note_section_widgets[i]
        sec_frame.destroy()
        break

  def save_notes_form(self, silent=False):
    if self.current_topic_index is None:
      return
    new_notes = []
    for h_ent, p_txt, f in self.note_section_widgets:
      heading = h_ent.get()
      points_raw = p_txt.get("1.0", tk.END).strip().split("\n")
      points = [pt.strip() for pt in points_raw if pt.strip()]
      new_notes.append({"heading": heading, "points": points})
    self.data["topics"][self.current_topic_index]["notes"] = new_notes
    if not silent:
      messagebox.showinfo("Success", "Notes updated successfully.")

  def init_terms_gui(self):
    top_ctrl = ttk.Frame(self.tab_terms, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(top_ctrl, text="+ Add Term", command=self.add_term_row).pack(
        side=tk.LEFT
    )
    ttk.Button(
        top_ctrl, text="Save Terms", command=lambda: self.save_terms_form(False)
    ).pack(side=tk.RIGHT)

    self.terms_canvas = tk.Canvas(self.tab_terms, highlightthickness=0)
    self.terms_scroll = ttk.Scrollbar(
        self.tab_terms, orient="vertical", command=self.terms_canvas.yview
    )
    self.terms_container = ttk.Frame(self.terms_canvas)
    self.terms_window_id = self.terms_canvas.create_window(
        (0, 0), window=self.terms_container, anchor="nw"
    )

    self.terms_container.bind(
        "<Configure>",
        lambda e: self.terms_canvas.configure(
            scrollregion=self.terms_canvas.bbox("all")
        ),
    )
    self.bind_responsive_canvas(self.terms_canvas, self.terms_window_id)
    self.terms_canvas.configure(yscrollcommand=self.terms_scroll.set)
    self.terms_canvas.pack(
        side="left", fill="both", expand=True, padx=5, pady=5
    )
    self.terms_scroll.pack(side="right", fill="y")
    self.term_widgets = []

  def load_terms_ui(self, terms_list):
    for w in self.terms_container.winfo_children():
      w.destroy()
    self.term_widgets = []
    for idx, item in enumerate(terms_list):
      row_f = ttk.Frame(self.terms_container, padding=2)
      row_f.pack(fill=tk.X, expand=True, pady=2)
      ttk.Label(row_f, text=f"Term {idx+1}:", width=8).pack(side=tk.LEFT)
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
    t = self.data["topics"][self.current_topic_index]
    if "key_terms" not in t:
      t["key_terms"] = []
    t["key_terms"].append({"term": "New Term", "definition": "Definition here."})
    self.load_terms_ui(t["key_terms"])

  def remove_term_row(self, row_f):
    for i, (t_ent, d_ent, f) in enumerate(self.term_widgets):
      if f == row_f:
        del self.term_widgets[i]
        row_f.destroy()
        break

  def save_terms_form(self, silent=False):
    if self.current_topic_index is None:
      return
    new_terms = []
    for t_ent, d_ent, f in self.term_widgets:
      new_terms.append({"term": t_ent.get(), "definition": d_ent.get()})
    self.data["topics"][self.current_topic_index]["key_terms"] = new_terms
    if not silent:
      messagebox.showinfo("Success", "Key terms updated successfully.")

  def init_flashcards_gui(self):
    top_ctrl = ttk.Frame(self.tab_flashcards, padding=5)
    top_ctrl.pack(fill=tk.X)
    ttk.Button(
        top_ctrl, text="+ Add Flashcard", command=self.add_fc_row
    ).pack(side=tk.LEFT)
    ttk.Button(
        top_ctrl, text="Save Flashcards", command=lambda: self.save_fc_form(False)
    ).pack(side=tk.RIGHT)

    self.fc_canvas = tk.Canvas(self.tab_flashcards, highlightthickness=0)
    self.fc_scroll = ttk.Scrollbar(
        self.tab_flashcards, orient="vertical", command=self.fc_canvas.yview
    )
    self.fc_container = ttk.Frame(self.fc_canvas)
    self.fc_window_id = self.fc_canvas.create_window(
        (0, 0), window=self.fc_container, anchor="nw"
    )

    self.fc_container.bind(
        "<Configure>",
        lambda e: self.fc_canvas.configure(
            scrollregion=self.fc_canvas.bbox("all")
        ),
    )
    self.bind_responsive_canvas(self.fc_canvas, self.fc_window_id)
    self.fc_canvas.configure(yscrollcommand=self.fc_scroll.set)
    self.fc_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    self.fc_scroll.pack(side="right", fill="y")
    self.fc_widgets = []

  def load_flashcards_ui(self, fc_list):
    for w in self.fc_container.winfo_children():
      w.destroy()
    self.fc_widgets = []
    for idx, fc in enumerate(fc_list):
      row_f = ttk.LabelFrame(
          self.fc_container, text=f"Flashcard {idx+1}", padding=8
      )
      row_f.pack(fill=tk.X, expand=True, padx=2, pady=4)

      f_frame = ttk.Frame(row_f)
      f_frame.pack(fill=tk.X, expand=True, pady=2)
      ttk.Label(f_frame, text="Front:", width=20).pack(side=tk.LEFT)
      f_ent = ttk.Entry(f_frame)
      f_ent.insert(0, fc.get("front", ""))
      f_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      b_frame = ttk.Frame(row_f)
      b_frame.pack(fill=tk.X, expand=True, pady=2)
      ttk.Label(b_frame, text="Back:", width=20).pack(side=tk.LEFT)
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
    t = self.data["topics"][self.current_topic_index]
    if "flashcards" not in t:
      t["flashcards"] = []
    t["flashcards"].append({"front": "Question?", "back": "Answer."})
    self.load_flashcards_ui(t["flashcards"])

  def remove_fc_row(self, row_f):
    for i, (f_ent, b_ent, f) in enumerate(self.fc_widgets):
      if f == row_f:
        del self.fc_widgets[i]
        row_f.destroy()
        break

  def save_fc_form(self, silent=False):
    if self.current_topic_index is None:
      return
    new_fcs = []
    for f_ent, b_ent, f in self.fc_widgets:
      new_fcs.append({"front": f_ent.get(), "back": b_ent.get()})
    self.data["topics"][self.current_topic_index]["flashcards"] = new_fcs
    if not silent:
      messagebox.showinfo("Success", "Flashcards updated successfully.")

  def init_questions_gui_optimized(self):
    q_paned = ttk.PanedWindow(self.tab_questions, orient=tk.HORIZONTAL)
    q_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    left_q_frame = ttk.Frame(q_paned, padding=5)
    q_paned.add(left_q_frame, weight=1)

    ttk.Label(
        left_q_frame, text="Questions List", font=("Segoe UI", 9, "bold")
    ).pack(anchor=tk.W, pady=2)

    self.q_listbox = tk.Listbox(left_q_frame, exportselection=False)
    self.q_listbox.pack(
        side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2
    )
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

    self.q_detail_canvas = tk.Canvas(right_q_frame, highlightthickness=0)
    self.q_detail_scroll = ttk.Scrollbar(
        right_q_frame, orient="vertical", command=self.q_detail_canvas.yview
    )
    self.q_detail_container = ttk.Frame(self.q_detail_canvas, padding=5)

    self.q_detail_window_id = self.q_detail_canvas.create_window(
        (0, 0), window=self.q_detail_container, anchor="nw"
    )
    self.q_detail_container.bind(
        "<Configure>",
        lambda e: self.q_detail_canvas.configure(
            scrollregion=self.q_detail_canvas.bbox("all")
        ),
    )
    self.bind_responsive_canvas(self.q_detail_canvas, self.q_detail_window_id)
    self.q_detail_canvas.configure(yscrollcommand=self.q_detail_scroll.set)

    self.q_detail_canvas.pack(
        side="left", fill="both", expand=True, padx=2, pady=2
    )
    self.q_detail_scroll.pack(side="right", fill="y")

    save_q_btn_frame = ttk.Frame(right_q_frame)
    save_q_btn_frame.pack(fill=tk.X, pady=5)
    ttk.Button(
        save_q_btn_frame,
        text="Save Question Changes",
        command=lambda: self.save_current_question_form(False),
    ).pack(side=tk.RIGHT)

  def load_questions_list_optimized(self):
    self.q_listbox.delete(0, tk.END)
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    questions = t.get("questions", [])
    for idx, q in enumerate(questions):
      q_type = q.get("type", "mcq")
      prompt_snip = q.get("prompt", "")[:35]
      self.q_listbox.insert(
          tk.END, f"Q{idx+1} [{q_type}]: {prompt_snip}..."
      )
    self.current_question_index = None
    for widget in self.q_detail_container.winfo_children():
      widget.destroy()

  def on_select_question_item(self, event):
    selected = self.q_listbox.curselection()
    if not selected:
      return
    if self.current_question_index is not None:
      self.save_current_question_form(silent=True)

    self.current_question_index = selected[0]
    self.render_single_question_form()

  def render_single_question_form(self):
    for widget in self.q_detail_container.winfo_children():
      widget.destroy()

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

    ttk.Label(
        self.q_detail_container,
        text=f"Editing Question {self.current_question_index+1} [{q_type.upper()}]",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor=tk.W, pady=5)

    p_box = ttk.Frame(self.q_detail_container)
    p_box.pack(fill=tk.X, pady=3)
    ttk.Label(p_box, text="Prompt:", width=12).pack(side=tk.LEFT)
    self.det_prompt_ent = ttk.Entry(p_box)
    self.det_prompt_ent.insert(0, q.get("prompt", ""))
    self.det_prompt_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    self.det_spec = {"type": q_type}

    if q_type == "mcq":
      ctx_box = ttk.Frame(self.q_detail_container)
      ctx_box.pack(fill=tk.X, pady=2)
      ttk.Label(ctx_box, text="Context:", width=12).pack(side=tk.LEFT)
      self.det_mcq_context = ttk.Entry(ctx_box)
      self.det_mcq_context.insert(0, q.get("context", ""))
      self.det_mcq_context.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      src_box = ttk.Frame(self.q_detail_container)
      src_box.pack(fill=tk.X, pady=2)
      ttk.Label(src_box, text="Source:", width=12).pack(side=tk.LEFT)
      self.det_mcq_source = ttk.Entry(src_box)
      self.det_mcq_source.insert(0, q.get("source", ""))
      self.det_mcq_source.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      opts = q.get("options", ["", "", "", ""])
      self.det_spec["opt_ents"] = []
      for o_idx, opt_text in enumerate(opts):
        o_box = ttk.Frame(self.q_detail_container)
        o_box.pack(fill=tk.X, pady=2)
        ttk.Label(o_box, text=f"Option {o_idx}:", width=12).pack(side=tk.LEFT)
        o_ent = ttk.Entry(o_box)
        o_ent.insert(0, opt_text)
        o_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.det_spec["opt_ents"].append(o_ent)

      ans_box = ttk.Frame(self.q_detail_container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Correct Index:", width=18).pack(side=tk.LEFT)
      self.det_ans_spin = ttk.Spinbox(
          ans_box, from_=0, to=max(3, len(opts) - 1), width=5
      )
      self.det_ans_spin.set(q.get("answer", 0))
      self.det_ans_spin.pack(side=tk.LEFT, padx=2)

    elif q_type == "truefalse":
      ans_box = ttk.Frame(self.q_detail_container)
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
      ans_box = ttk.Frame(self.q_detail_container)
      ans_box.pack(fill=tk.X, pady=3)
      ttk.Label(ans_box, text="Model Answer:", width=15).pack(side=tk.LEFT)
      self.det_short_ent = ttk.Entry(ans_box)
      self.det_short_ent.insert(0, q.get("answer", ""))
      self.det_short_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    elif q_type == "cloze":
      ans_box = ttk.Frame(self.q_detail_container)
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
      pf_box = ttk.LabelFrame(
          self.q_detail_container, text="Pairs (Left : Right)", padding=5
      )
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
      q_box = ttk.Frame(self.q_detail_container)
      q_box.pack(fill=tk.X, pady=3)
      ttk.Label(q_box, text="Quote:", width=10).pack(side=tk.LEFT)
      self.det_quote_ent = ttk.Entry(q_box)
      self.det_quote_ent.insert(0, q.get("quote", ""))
      self.det_quote_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      src_tfs_box = ttk.Frame(self.q_detail_container)
      src_tfs_box.pack(fill=tk.X, pady=3)
      ttk.Label(src_tfs_box, text="Source:", width=10).pack(side=tk.LEFT)
      self.det_tfs_source = ttk.Entry(src_tfs_box)
      self.det_tfs_source.insert(0, q.get("source", ""))
      self.det_tfs_source.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

      items = q.get("items", [])
      self.det_spec["tfs_item_ents"] = []
      tfs_box = ttk.LabelFrame(
          self.q_detail_container, text="Statements & Answers", padding=5
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

    exp_box = ttk.Frame(self.q_detail_container)
    exp_box.pack(fill=tk.X, pady=3)
    ttk.Label(exp_box, text="Explanation:", width=12).pack(side=tk.LEFT)
    self.det_exp_ent = ttk.Entry(exp_box)
    self.det_exp_ent.insert(0, q.get("explanation", ""))
    self.det_exp_ent.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

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
      except:
        q["answer"] = 0
      ctx_val = self.det_mcq_context.get().strip()
      if ctx_val:
        q["context"] = ctx_val
      elif "context" in q:
        del q["context"]

      src_val = self.det_mcq_source.get().strip()
      if src_val:
        q["source"] = src_val
      elif "source" in q:
        del q["source"]

    elif q_type == "truefalse":
      q["answer"] = self.det_tf_var.get() == "True"
    elif q_type == "short":
      q["answer"] = self.det_short_ent.get()
    elif q_type == "cloze":
      ans_str = self.det_cloze_ent.get()
      q["answers"] = [a.strip() for a in ans_str.split(",") if a.strip()]
    elif q_type == "match":
      pairs = []
      for l_ent, r_ent in self.det_spec["pair_ents"]:
        pairs.append({"left": l_ent.get(), "right": r_ent.get()})
      q["pairs"] = pairs
    elif q_type == "tfs":
      q["quote"] = self.det_quote_ent.get()
      src_val = self.det_tfs_source.get().strip()
      if src_val:
        q["source"] = src_val
      elif "source" in q:
        del q["source"]

      items = []
      for txt_ent, ans_var in self.det_spec["tfs_item_ents"]:
        items.append({"text": txt_ent.get(), "answer": ans_var.get() == "True"})
      q["items"] = items

    curr_idx = self.current_question_index
    prompt_snip = q.get("prompt", "")[:35]
    self.q_listbox.delete(curr_idx)
    self.q_listbox.insert(
        curr_idx, f"Q{curr_idx+1} [{q_type}]: {prompt_snip}..."
    )
    self.q_listbox.selection_set(curr_idx)

    if not silent:
      messagebox.showinfo("Success", "Question updated successfully.")

  def add_single_question(self):
    if self.current_topic_index is None:
      return
    t = self.data["topics"][self.current_topic_index]
    if "questions" not in t:
      t["questions"] = []

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

    t["questions"].append(new_q)
    self.load_questions_list_optimized()
    self.q_listbox.selection_set(len(t["questions"]) - 1)
    self.on_select_question_item(None)

  def delete_single_question(self):
    selected = self.q_listbox.curselection()
    if not selected or self.current_topic_index is None:
      return
    idx = selected[0]
    t = self.data["topics"][self.current_topic_index]
    del t["questions"][idx]
    self.load_questions_list_optimized()
    for widget in self.q_detail_container.winfo_children():
      widget.destroy()
    self.current_question_index = None


if __name__ == "__main__":
  root = tk.Tk()
  app = StudyPackEditor(root)
  root.mainloop()
