"""
Dateiverwaltungsfunktionen für die STL3D-Anwendung
"""

import os
import sys
import tkinter.messagebox as mb

def setup_drag_drop(widget, callback):
    """
    Richtet Drag & Drop für die Anwendung ein.
    
    Args:
        widget: Das Tkinter-Widget, das Drag & Drop unterstützen soll
        callback: Eine Funktion, die mit einer Liste von Dateipfaden aufgerufen wird
    """
    try:
        # Windows
        if sys.platform == 'win32':
            try:
                import win32gui
                import win32con
                import win32api
                
                def py_drop_file(hwnd, file_list):
                    # Konvertiere Pfade von ANSI zu Unicode, falls nötig
                    files = []
                    for f in file_list:
                        if isinstance(f, bytes):
                            files.append(f.decode('ansi'))
                        else:
                            files.append(f)
                    
                    callback(files)
                    return True
                
                def py_drop_file_hwnd(hwnd, msg, wparam, lparam):
                    if msg == win32con.WM_DROPFILES:
                        drop_hwnd = win32gui.DragQueryPoint(wparam)
                        files = win32gui.DragQueryFile(wparam)
                        win32gui.DragFinish(wparam)
                        py_drop_file(hwnd, files)
                    return True
                
                hwnd = widget.winfo_id()
                old_windproc = win32gui.SetWindowLong(hwnd, win32con.GWL_WNDPROC, py_drop_file_hwnd)
                win32gui.DragAcceptFiles(hwnd, True)
                
                print("Drag & Drop für Windows eingerichtet")
            except ImportError:
                print("pywin32 nicht installiert. Drag & Drop unter Windows nicht verfügbar.")
                mb.showinfo("Hinweis", "Für Drag & Drop unter Windows wird pywin32 benötigt.\nInstalliere mit: pip install pywin32")
        
        # macOS und Linux über TkDND
        else:
            try:
                # Versuche TkDND zu laden
                widget.tk.call('package', 'require', 'tkdnd')
                
                def _on_drop(event):
                    files = event.data.split()
                    # Entferne {}-Klammern, falls vorhanden
                    files = [f.strip('{}') for f in files]
                    callback(files)
                    return event.action
                
                widget.drop_target_register('DND_Files')
                widget.dnd_bind('<<Drop>>', _on_drop)
                
                print("Drag & Drop für Unix/macOS eingerichtet")
            except Exception as e:
                print(f"TkDND konnte nicht geladen werden: {str(e)}")
                print("Drag & Drop wird nicht verfügbar sein.")
                
                # Warnung anzeigen
                mb.showinfo("Hinweis", 
                          "Für Drag & Drop unter macOS/Linux wird TkDND benötigt.\n"
                          "Installiere es über deinen Paketmanager.")
    
    except Exception as e:
        print(f"Drag & Drop-Setup fehlgeschlagen: {str(e)}")

def ensure_directory_exists(path):
    """
    Stellt sicher, dass ein Verzeichnis existiert und erstellt es bei Bedarf.
    
    Args:
        path: Pfad zum Verzeichnis
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
