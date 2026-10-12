import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class StudyPackEditor:

  def __init__(self, root):
    self.root = root
    self.root.title("Study Pack JSON Editor")
    self.root.geometry("1100x750")

    # Dữ liệu mặc định
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
    self.create_widgets()

  def create_widgets(self):
    # Menu Bar
    menubar = tk.Menu(self.root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="New Study Pack", command=self.new_file)
    file_menu.add_command(
        label="Open JSON File...", command=self.open_file, accelerator="Ctrl+O"
    )
    file_menu.add_command(
        label="Save JSON File...", command=self.save_file, accelerator="Ctrl+S"
    )
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)
    menubar.add_cascade(label="File", menu=file_menu)
    self.root.config(menu=menubar)

    # Khung chính chia 2 cột: Trái (Danh sách Topics), Phải (Chi tiết chỉnh sửa)
    main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # --- CỘT TRÁI: Metadata & Topics ---
    left_frame = ttk.Frame(main_paned, padding=5)
    main_paned.add(left_frame, weight=1)

    # Metadata Frame
    meta_frame = ttk.LabelFrame(left_frame, text="Study Pack Info", padding=5)
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
          row=idx, column=0, sticky=tk.W, pady=2
      )
      ent = ttk.Entry(meta_frame, width=25)
      ent.grid(row=idx, column=1, sticky=tk.EW, pady=2)
      ent.bind(
          "<FocusOut>", lambda e, k=key, entry=ent: self.update_meta(k, entry)
      )
      self.meta_entries[key] = ent
    meta_frame.columnconfigure(1, weight=1)

    # Topics List Frame
    topic_frame = ttk.LabelFrame(left_frame, text="Topics", padding=5)
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

    # --- CỘT PHẢI: Chi tiết Topic (Notebook tabs) ---
    self.right_frame = ttk.Frame(main_paned, padding=5)
    main_paned.add(self.right_frame, weight=3)

    # Topic General info
    top_info_frame = ttk.Frame(self.right_frame)
    top_info_frame.pack(fill=tk.X, pady=2)

    ttk.Label(top_info_frame, text="Topic ID:").grid(
        row=0, column=0, sticky=tk.W, padx=2
    )
    self.t_id_var = tk.StringVar()
    self.t_id_ent = ttk.Entry(
        top_info_frame, textvariable=self.t_id_var, width=10
    )
    self.t_id_ent.grid(row=0, column=1, sticky=tk.W, padx=2)
    self.t_id_ent.bind(
        "<FocusOut>", lambda e: self.update_current_topic_field("id", self.t_id_var)
    )

    ttk.Label(top_info_frame, text="Topic Title:").grid(
        row=0, column=2, sticky=tk.W, padx=2
    )
    self.t_title_var = tk.StringVar()
    self.t_title_ent = ttk.Entry(
        top_info_frame, textvariable=self.t_title_var, width=30
    )
    self.t_title_ent.grid(row=0, column=3, sticky=tk.EW, padx=2)
    self.t_title_ent.bind(
        "<FocusOut>",
        lambda e: self.update_current_topic_field(
            "title", self.t_title_var
        ),
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
        lambda e: self.update_current_topic_field(
            "summary", self.t_summary_var
        ),
    )

    # Sub-tabs cho Notes, Key Terms, Flashcards, Questions
    self.notebook = ttk.Notebook(self.right_frame)
    self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

    self.tab_notes = ttk.Frame(self.notebook)
    self.tab_terms = ttk.Frame(self.notebook)
    self.tab_flashcards = ttk.Frame(self.notebook)
    self.tab_questions = ttk.Frame(self.notebook)

    self.notebook.add(self.tab_notes, text="Notes")
    self.notebook.add(self.tab_terms, text="Key Terms")
    self.notebook.add(self.tab_flashcards, text="Flashcards")
    self.notebook.add(self.tab_questions, text="Questions")

    self.init_notes_tab()
    self.init_terms_tab()
    self.init_flashcards_tab()
    self.init_questions_tab()

  # --- QUẢN LÝ FILE & METADATA ---
  def new_file(self):
    if messagebox.askyesno(
        "New", "Create new study pack? Unsaved changes will be lost."
    ):
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
        messagebox.load = file_path
        messagebox.showinfo("Success", "Loaded study pack successfully!")
      except Exception as e:
        messagebox.showerror("Error", f"Could not read JSON file:\n{e}")

  def save_file(self):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if file_path:
      try:
        with open(file_path, "w", encoding="utf-8") as f:
          json.dump(self.data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Success", "Saved study pack successfully!")
      except Exception as e:
        messagebox.showerror("Error", f"Could not save file:\n{e}")

  def update_meta(self, key, entry):
    self.data[key] = entry.get()

  def refresh_ui(self):
    # Cập nhật metadata entries
    for key, ent in self.meta_entries.items():
      ent.delete(0, tk.END)
      ent.insert(0, str(self.data.get(key, "")))

    # Cập nhật danh sách topics
    self.topic_listbox.delete(0, tk.END)
    for t in self.data.get("topics", []):
      self.topic_listbox.insert(
          tk.END, f"{t.get('id', '')}: {t.get('title', 'Untitled')}"
      )

    self.current_topic_index = None
    self.clear_topic_details()

  def clear_topic_details(self):
    self.t_id_var.set("")
    self.t_title_var.set("")
    self.t_summary_var.set("")
    self.notes_text.delete("1.0", tk.END)
    self.terms_text.delete("1.0", tk.END)
    self.fc_text.delete("1.0", tk.END)
    self.q_text.delete("1.0", tk.END)

  # --- TOPIC MANAGEMENT ---
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
    selected = self.topic_listbox.curselection()
    if not selected:
      return
    self.current_topic_index = selected[0]
    t = self.data["topics"][self.current_topic_index]

    self.t_id_var.set(t.get("id", ""))
    self.t_title_var.set(t.get("title", ""))
    self.t_summary_var.set(t.get("summary", ""))

    # Hiển thị dữ liệu thô dạng JSON được định dạng đẹp cho từng thành phần (dễ xem và sửa trực tiếp từng phần)
    self.notes_text.delete("1.0", tk.END)
    self.notes_text.insert(
        tk.END, json.dumps(t.get("notes", []), ensure_ascii=False, indent=2)
    )

    self.terms_text.delete("1.0", tk.END)
    self.terms_text.insert(
        tk.END, json.dumps(t.get("key_terms", []), ensure_ascii=False, indent=2)
    )

    self.fc_text.delete("1.0", tk.END)
    self.fc_text.insert(
        tk.END, json.dumps(t.get("flashcards", []), ensure_ascii=False, indent=2)
    )

    self.q_text.delete("1.0", tk.END)
    self.q_text.insert(
        tk.END, json.dumps(t.get("questions", []), ensure_ascii=False, indent=2)
    )

  def update_current_topic_field(self, field, var):
    if self.current_topic_index is not None:
      self.data["topics"][self.current_topic_index][field] = var.get()
      # Cập nhật lại tên trên listbox nếu đổi id hoặc title
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

  # --- TẠO CÁC TAB CHỈNH SỬA (Dạng JSON segment để tối ưu tốc độ linh hoạt) ---
  def init_notes_tab(self):
    lbl = ttk.Label(
        self.tab_notes,
        text=(
            "Edit Notes (JSON format: list of sections with heading and points"
            " with **bold** terms):"
        ),
    )
    lbl.pack(anchor=tk.W, padx=5, pady=5)
    self.notes_text = tk.Text(self.tab_notes, wrap=tk.WORD, height=20)
    self.notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    ttk.Button(
        self.tab_notes,
        text="Save Notes Changes",
        command=lambda: self.save_tab_json("notes", self.notes_text),
    ).pack(anchor=tk.E, padx=5, pady=5)

  def init_terms_tab(self):
    lbl = ttk.Label(
        self.tab_terms,
        text="Edit Key Terms (JSON format: list of {'term': ..., 'definition':"
        " ...}):",
    )
    lbl.pack(anchor=tk.W, padx=5, pady=5)
    self.terms_text = tk.Text(self.tab_terms, wrap=tk.WORD, height=20)
    self.terms_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    ttk.Button(
        self.tab_terms,
        text="Save Key Terms Changes",
        command=lambda: self.save_tab_json("key_terms", self.terms_text),
    ).pack(anchor=tk.E, padx=5, pady=5)

  def init_flashcards_tab(self):
    lbl = ttk.Label(
        self.tab_flashcards,
        text="Edit Flashcards (JSON format: list of {'front': ..., 'back':"
        " ...}):",
    )
    lbl.pack(anchor=tk.W, padx=5, pady=5)
    self.fc_text = tk.Text(self.tab_flashcards, wrap=tk.WORD, height=20)
    self.fc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    ttk.Button(
        self.tab_flashcards,
        text="Save Flashcards Changes",
        command=lambda: self.save_tab_json("flashcards", self.fc_text),
    ).pack(anchor=tk.E, padx=5, pady=5)

  def init_questions_tab(self):
    lbl = ttk.Label(
        self.tab_questions,
        text="Edit Questions (JSON format: list of objects with types: mcq,"
        " truefalse, short, tfs, cloze, match):",
    )
    lbl.pack(anchor=tk.W, padx=5, pady=5)
    self.q_text = tk.Text(self.tab_questions, wrap=tk.WORD, height=20)
    self.q_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    ttk.Button(
        self.tab_questions,
        text="Save Questions Changes",
        command=lambda: self.save_tab_json("questions", self.q_text),
    ).pack(anchor=tk.E, padx=5, pady=5)

  def save_tab_json(self, field_key, text_widget):
    if self.current_topic_index is None:
      messagebox.showwarning("Warning", "Please select a topic first!")
      return
    raw_content = text_widget.get("1.0", tk.END).strip()
    try:
      parsed_data = json.loads(raw_content)
      self.data["topics"][self.current_topic_index][field_key] = parsed_data
      messagebox.showinfo("Success", f"Successfully updated '{field_key}'!")
    except json.JSONDecodeError as e:
      messagebox.showerror(
          "JSON Error",
          f"Invalid JSON format. Please check your syntax:\n{e}",
      )


if __name__ == "__main__":
  root = tk.Tk()
  app = StudyPackEditor(root)
  root.mainloop()
