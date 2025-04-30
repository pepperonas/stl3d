"""
Funktionen für macOS-spezifische Kompatibilität
"""

import sys
import os
import tkinter as tk

def setup_mac_drag_drop(root):
    """
    Konfiguriert Drag & Drop für macOS (über AppleScript)
    
    Args:
        root: Das Hauptfenster (Tkinter Root-Objekt)
    """
    if sys.platform != 'darwin':
        return  # Nur für macOS

    try:
        # macOS-spezifische Drag & Drop-Einrichtung via AppleEvents
        # Diese Methode erfordert keine zusätzlichen Bibliotheken
        
        def handle_open_file(paths):
            """Verarbeitet die vom AppleScript übergebenen Dateipfade"""
            if isinstance(paths, list) and len(paths) > 0:
                # Sende ein benutzerdefiniertes Event an das Root-Fenster
                root.event_generate('<<MacFileDropped>>', data=paths[0])
                return True
            return False
        
        # Registriere beim macOS-System, dass wir Dateien per Drag & Drop akzeptieren
        root.createcommand('::tk::mac::OpenDocument', handle_open_file)
        
        print("macOS Drag & Drop eingerichtet")
    except Exception as e:
        print(f"Konnte macOS Drag & Drop nicht einrichten: {str(e)}")

def setup_mac_menu(root):
    """
    Konfiguriert das macOS-spezifische Menü
    
    Args:
        root: Das Hauptfenster (Tkinter Root-Objekt)
    """
    if sys.platform != 'darwin':
        return  # Nur für macOS
    
    try:
        # Standard-Menüs von macOS deaktivieren
        root.createcommand('::tk::mac::ShowPreferences', lambda: None)
        
        # "Über"-Dialog für macOS App-Menü konfigurieren
        def show_about_dialog():
            about_text = """3D-Modellierung aus Bildern

Eine Sammlung von Python-Werkzeugen zur Umwandlung von Bildern
in 3D-Modelle für den 3D-Druck.

Entwickelt von: Martin Pfeffer

Version: 1.0
Lizenz: MIT License
"""
            tk.messagebox.showinfo("Über 3D-Modellierung aus Bildern", about_text)
        
        root.createcommand('::tk::mac::ShowHelp', show_about_dialog)
        
        print("macOS-Menü konfiguriert")
    except Exception as e:
        print(f"Konnte macOS-Menü nicht konfigurieren: {str(e)}")
