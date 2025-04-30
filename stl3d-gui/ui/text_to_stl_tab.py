"""
UI-Komponente für den Text-to-STL Tab
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog

from PIL import Image, ImageTk
from modules.text_to_stl import text_to_stl, generate_preview_image
from resources.styles import COLORS
from utils.gui_utils import create_button, create_labeled_entry, create_log_area


class TextToSTLTab:
    """Tab für die Umwandlung von Text in STL-Dateien"""

    def __init__(self, parent, status_var, log_redirect):
        """
        Initialisiert den Tab für Text zu STL.

        Args:
            parent: Das übergeordnete Widget (der Tab)
            status_var: StringVar für die Statusleiste
            log_redirect: RedirectText-Objekt für die Ausgabeumleitung
        """
        self.parent = parent
        self.status_var = status_var
        self.log_redirect = log_redirect

        # Variablen für UI-Elemente
        self.text_var = tk.StringVar(value="")
        self.font_path_var = tk.StringVar(value="")
        self.font_size_var = tk.IntVar(value=120)
        self.thickness_var = tk.DoubleVar(value=10.0)
        self.filename_var = tk.StringVar(value="text_3d")
        self.add_base_var = tk.BooleanVar(value=True)
        self.base_height_var = tk.DoubleVar(value=2.0)
        self.mirror_text_var = tk.BooleanVar(value=False)
        self.blur_radius_var = tk.DoubleVar(value=0.0)
        self.timestamp_var = tk.BooleanVar(value=True)

        # Für die Vorschau
        self.preview_image = None
        self.preview_label = None

        self.create_widgets()

    def create_widgets(self):
        """Erstellt die UI-Elemente"""
        # Hauptframe mit zwei Spalten (links Eingaben, rechts Vorschau)
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Linke Spalte für Eingaben
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Rechte Spalte für Vorschau
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        # Texteingabe
        text_frame = ttk.LabelFrame(left_frame, text="Text")
        text_frame.pack(fill=tk.X, pady=10)

        # Text-Eingabefeld
        self.text_entry = tk.Text(text_frame, height=3, width=30, wrap=tk.WORD)
        self.text_entry.pack(fill=tk.X, padx=10, pady=10)
        self.text_entry.bind("<KeyRelease>", self.update_preview)

        # Schriftart-Frame
        font_frame = ttk.Frame(left_frame)
        font_frame.pack(fill=tk.X, pady=10)

        # Schriftart
        font_label = ttk.Label(font_frame, text="Schriftart:")
        font_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.font_entry = ttk.Entry(font_frame, textvariable=self.font_path_var, width=30)
        self.font_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)

        font_btn = create_button(font_frame, text="Durchsuchen", command=self.browse_font)
        font_btn.grid(row=0, column=2, padx=5)

        font_frame.columnconfigure(1, weight=1)

        # Parameter-Frame
        param_frame = ttk.LabelFrame(left_frame, text="Parameter")
        param_frame.pack(fill=tk.X, pady=10)

        # Allgemeine Parameter
        general_frame = ttk.Frame(param_frame)
        general_frame.pack(fill=tk.X, padx=10, pady=5)

        # Zeile 1: Schriftgröße, Dicke
        font_size_frame = create_labeled_entry(general_frame, "Schriftgröße (Pt):",
                                               self.font_size_var, width=8)
        font_size_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        font_size_frame.bind("<FocusOut>", self.update_preview)

        thickness_frame = create_labeled_entry(general_frame, "Dicke (mm):",
                                               self.thickness_var, width=8)
        thickness_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Zeile 2: Ausgabedatei
        filename_label = ttk.Label(general_frame, text="Ausgabedatei:")
        filename_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        filename_entry = ttk.Entry(general_frame, textvariable=self.filename_var, width=30)
        filename_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # Zeile 3: Weichzeichnen
        blur_frame = create_labeled_entry(general_frame, "Weichzeichnen (0-5):",
                                          self.blur_radius_var, width=8)
        blur_frame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        # Basis-Optionen
        base_frame = ttk.LabelFrame(param_frame, text="Basis-Optionen")
        base_frame.pack(fill=tk.X, padx=10, pady=5)

        add_base_check = ttk.Checkbutton(base_frame, text="Bodenplatte hinzufügen",
                                         variable=self.add_base_var, command=self.toggle_base_height)
        add_base_check.pack(side=tk.LEFT, padx=5, pady=5)

        self.base_height_frame = create_labeled_entry(base_frame, "Höhe (mm):",
                                                      self.base_height_var, width=8)
        self.base_height_frame.pack(side=tk.LEFT, padx=5, pady=5)

        # Sonstige Checkboxen
        checkbox_frame = ttk.Frame(param_frame)
        checkbox_frame.pack(fill=tk.X, padx=10, pady=5)

        mirror_check = ttk.Checkbutton(checkbox_frame, text="Text spiegeln",
                                       variable=self.mirror_text_var, command=self.update_preview)
        mirror_check.pack(side=tk.LEFT, padx=5)

        timestamp_check = ttk.Checkbutton(checkbox_frame, text="Zeitstempel hinzufügen",
                                          variable=self.timestamp_var)
        timestamp_check.pack(side=tk.LEFT, padx=5)

        # Button-Frame
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)

        update_preview_btn = create_button(button_frame, text="Vorschau aktualisieren",
                                           command=self.update_preview)
        update_preview_btn.pack(side=tk.LEFT, padx=5)

        convert_btn = create_button(button_frame, text="Text in STL konvertieren",
                                    command=self.create_text_stl)
        convert_btn.pack(side=tk.LEFT, padx=5)

        # Log-Bereich
        log_frame, self.log_text = create_log_area(left_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Rechte Spalte - Vorschau
        preview_frame = ttk.LabelFrame(right_frame, text="Vorschau")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Platzhalter für die Vorschau
        self.preview_label = ttk.Label(preview_frame, text="Gib Text ein, um eine Vorschau zu sehen")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Initialisierung
        self.toggle_base_height()
        self.update_preview()

    def browse_font(self):
        """Öffnet einen Dateiauswahldialog für die Schriftart"""
        filetypes = [
            ("TrueType Fonts", "*.ttf"),
            ("OpenType Fonts", "*.otf"),
            ("TrueType Collection", "*.ttc"),
            ("Alle Dateien", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.font_path_var.set(filename)
            # Aktualisiere die Vorschau
            self.update_preview()

    def toggle_base_height(self):
        """Aktiviert oder deaktiviert die Basis-Höhen-Eingabe"""
        if self.add_base_var.get():
            for child in self.base_height_frame.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.base_height_frame.winfo_children():
                child.configure(state='disabled')

    def update_preview(self, event=None):
        """Aktualisiert die Vorschau des Textes"""
        # Text aus dem Textfeld holen
        text = self.text_entry.get("1.0", tk.END).strip()
        if not text:
            self.preview_label.configure(text="Gib Text ein, um eine Vorschau zu sehen")
            self.text_var.set("")
            return

        self.text_var.set(text)

        # Vorschaubild generieren
        font_path = self.font_path_var.get()
        font_size = self.font_size_var.get()
        mirror_text = self.mirror_text_var.get()

        # Pfad für das temporäre Vorschaubild
        preview_path = os.path.join("output", "text-to-stl", "temp_preview.png")
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)

        # Vorschau generieren
        preview_image = generate_preview_image(text, font_path, font_size, preview_path)

        if preview_image:
            # Wenn ein Vorschaubild generiert wurde, zeige es an
            if mirror_text:
                preview_image = preview_image.transpose(Image.FLIP_LEFT_RIGHT)

            # Bild in eine Größe bringen, die gut angezeigt werden kann
            width, height = preview_image.size
            max_width = 400
            max_height = 300

            if width > max_width or height > max_height:
                # Skalierungsfaktor berechnen
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                preview_image = preview_image.resize((new_width, new_height), Image.LANCZOS)

            # In Tkinter-Format konvertieren
            self.preview_photo = ImageTk.PhotoImage(preview_image)

            # Vorschau anzeigen
            if isinstance(self.preview_label, ttk.Label):
                self.preview_label.destroy()

            self.preview_label = ttk.Label(self.preview_label.master, image=self.preview_photo)
            self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Status aktualisieren
            self.status_var.set("Vorschau aktualisiert")
        else:
            # Bei Fehler Textmeldung anzeigen
            self.preview_label.configure(text="Fehler bei der Vorschauerstellung")

            # Status aktualisieren
            self.status_var.set("Fehler bei der Vorschauerstellung")

    def create_text_stl(self):
        """Erstellt eine STL-Datei aus dem Text"""
        # Text aus dem Textfeld holen
        text = self.text_entry.get("1.0", tk.END).strip()

        if not text:
            self.status_var.set("Fehler: Kein Text eingegeben")
            return

        try:
            # Parameter aus den UI-Elementen holen
            font_path = self.font_path_var.get() if self.font_path_var.get() else None
            font_size = self.font_size_var.get()
            thickness = self.thickness_var.get()
            filename = self.filename_var.get()
            add_base = self.add_base_var.get()
            base_height = self.base_height_var.get() if add_base else 0.0
            mirror_text = self.mirror_text_var.get()
            blur_radius = self.blur_radius_var.get()
            use_timestamp = self.timestamp_var.get()

            # Status aktualisieren
            self.status_var.set("Erstelle 3D-Modell aus Text...")

            # Log-Bereich leeren
            self.log_text.configure(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.configure(state="disabled")

            # Alle Parameter in ein Dictionary packen
            params = {
                'text': text,
                'font_path': font_path,
                'font_size': font_size,
                'thickness': thickness,
                'filename': filename,
                'add_base': add_base,
                'base_height': base_height,
                'mirror_text': mirror_text,
                'blur_radius': blur_radius,
                'use_timestamp': use_timestamp
            }

            # Verarbeitung in einem separaten Thread starten
            import threading
            thread = threading.Thread(target=self._run_text_to_stl_wrapper, args=(params,))
            thread.daemon = True
            thread.start()

        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Eingabevalidierung: {str(e)}"
            self.status_var.set(error_msg)
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{error_msg}\n{traceback.format_exc()}")
            self.log_text.configure(state="disabled")

    def _run_text_to_stl_wrapper(self, params):
        """
        Wrapper für _run_text_to_stl, der die Parameter aus einem Dictionary nimmt.
        """
        try:
            # Parameter aus dem Dictionary extrahieren
            self._run_text_to_stl(
                params['text'],
                params['font_path'],
                params['font_size'],
                params['thickness'],
                params['filename'],
                params['add_base'],
                params['base_height'],
                params['mirror_text'],
                params['blur_radius'],
                params['use_timestamp']
            )
        except Exception as e:
            import traceback
            error_msg = f"Fehler bei der Text-zu-STL Verarbeitung: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())

    def _run_text_to_stl(self, text, font_path, font_size, thickness, filename,
                         add_base, base_height, mirror_text, blur_radius, use_timestamp):
        """
        Führt die Text-zu-STL Konvertierung in einem separaten Thread aus.

        Args:
            Alle Parameter werden von create_text_stl() übergeben
        """
        try:
            # Verarbeitung durchführen
            print(f"Verarbeite Text: '{text}'")
            print(f"Parameter: font_size={font_size}, thickness={thickness}")
            print(f"add_base={add_base}, base_height={base_height}")
            print(f"mirror_text={mirror_text}, blur_radius={blur_radius}")

            result_path = text_to_stl(
                text, font_path, font_size, thickness, filename,
                add_base, base_height, mirror_text, blur_radius, use_timestamp
            )

            if result_path:
                # Status aktualisieren
                self.status_var.set(f"Text-zu-STL Konvertierung abgeschlossen: {result_path}")
            else:
                # Status aktualisieren
                self.status_var.set("Fehler bei der Text-zu-STL Konvertierung")

        except Exception as e:
            print(f"Fehler bei der Text-zu-STL Konvertierung: {str(e)}")
            self.status_var.set("Fehler bei der Text-zu-STL Konvertierung")
