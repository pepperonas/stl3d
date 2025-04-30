#!/usr/bin/env python3
"""
3D-Modellierung aus Bildern - Eine GUI-Anwendung

Dieses Programm integriert verschiedene Werkzeuge zur Umwandlung von Bildern 
in 3D-Modelle und zur Reparatur von STL-Dateien.

Entwickelt von: Martin Pfeffer
"""

import os
import sys
from app import STL3DApp

if __name__ == "__main__":
    app = STL3DApp()
    app.run()
