"""
Validierungsfunktionen für Eingabefelder
"""

import tkinter as tk
import re

def validate_numeric(value):
    """
    Überprüft, ob ein Wert eine gültige Zahl ist.
    
    Args:
        value: Der zu überprüfende Wert
        
    Returns:
        True, wenn der Wert eine gültige Zahl ist, sonst False
    """
    if value == "":
        return True  # Leere Eingabe ist erlaubt
    
    # Erlaube Zahlen (inkl. negativen Zahlen und Dezimalstellen)
    pattern = r'^[-+]?[0-9]*\.?[0-9]+$'
    return bool(re.match(pattern, value))

def register_numeric_validation(entry_widget):
    """
    Registriert eine Validierungsfunktion für ein Eingabefeld,
    die nur numerische Eingaben zulässt.
    
    Args:
        entry_widget: Das Tkinter-Entry-Widget
    """
    vcmd = (entry_widget.register(validate_numeric), '%P')
    entry_widget.configure(validate="key", validatecommand=vcmd)

def create_numeric_entry(parent, textvariable, width=None):
    """
    Erstellt ein Eingabefeld, das nur numerische Eingaben akzeptiert.
    
    Args:
        parent: Das übergeordnete Widget
        textvariable: Tkinter-Variable für den Wert
        width: Breite des Eingabefelds
        
    Returns:
        Das erstellte Entry-Widget
    """
    entry = tk.Entry(parent, textvariable=textvariable, width=width)
    register_numeric_validation(entry)
    return entry
