"""
Hilfsfunktionen für die GUI-Komponenten der STL3D-Anwendung
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from resources.styles import COLORS

def create_tab(notebook, title):
    """
    Erstellt einen Tab im Notebook mit dem richtigen Stil.
    
    Args:
        notebook: Das Notebook-Widget
        title: Titel des Tabs
        
    Returns:
        Der erstellte Frame für den Tab
    """
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=title)
    return tab

def create_button(parent, text, command=None, width=None):
    """
    Erstellt einen Button im Material Design-Stil.
    
    Args:
        parent: Das übergeordnete Widget
        text: Text auf dem Button
        command: Funktion, die beim Klicken ausgeführt wird
        width: Breite des Buttons
        
    Returns:
        Der erstellte Button
    """
    btn = ttk.Button(parent, text=text, command=command, width=width)
    return btn

def create_labeled_entry(parent, label_text, variable, width=None):
    """
    Erstellt ein Eingabefeld mit Beschriftung.
    
    Args:
        parent: Das übergeordnete Widget
        label_text: Text der Beschriftung
        variable: Tkinter-Variable für den Wert
        width: Breite des Eingabefelds
        
    Returns:
        Der erstellte Frame mit Label und Eingabefeld
    """
    from utils.validate_entry import create_numeric_entry
    
    frame = ttk.Frame(parent)
    
    label = ttk.Label(frame, text=label_text)
    label.pack(side=tk.LEFT, padx=(0, 5))
    
    # Prüfen, ob es sich um eine numerische Variable handelt
    if isinstance(variable, (tk.IntVar, tk.DoubleVar)):
        entry = create_numeric_entry(frame, variable, width)
    else:
        entry = ttk.Entry(frame, textvariable=variable, width=width)
    
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    return frame

def create_log_area(parent):
    """
    Erstellt ein scrollbares Textfeld für Logausgaben.
    
    Args:
        parent: Das übergeordnete Widget
        
    Returns:
        Ein Tupel (frame, text_widget) mit dem Frame und dem Textfeld
    """
    frame = ttk.Frame(parent)
    
    log_label = ttk.Label(frame, text="Log:")
    log_label.pack(anchor=tk.W, pady=(0, 5))
    
    log_text = scrolledtext.ScrolledText(frame, height=15, bg=COLORS["primary_light"], 
                                        fg=COLORS["text"], font=('Courier', 9))
    log_text.pack(fill=tk.BOTH, expand=True)
    log_text.configure(state="disabled")  # Schreibgeschützt
    
    return frame, log_text

class RedirectText:
    """Klasse zum Umleiten von stdout in ein Tkinter-Textfeld"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        
    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")
        
    def flush(self):
        pass
