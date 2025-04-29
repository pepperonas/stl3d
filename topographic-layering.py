#!/usr/bin/env python3
# Topographic Layering Tool
# Erstellt ein 3D-Modell aus einem JPG-Bild

import argparse
import os
import sys
import datetime

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from stl import mesh
from tqdm import tqdm


def load_image(image_path):
    """Lädt ein Bild und konvertiert es zu Graustufen."""
    try:
        img = Image.open(image_path).convert('L')
        return np.array(img)
    except Exception as e:
        raise Exception(f"Fehler beim Laden des Bildes: {e}")


def normalize_heightmap(heightmap):
    """Normalisiert die Höhenwerte auf einen Bereich von 0 bis 1."""
    min_val = np.min(heightmap)
    max_val = np.max(heightmap)
    return (heightmap - min_val) / (max_val - min_val)


def create_mesh(heightmap, scale_z=10.0, smoothing=1, resolution=1):
    """Erstellt ein 3D-Mesh aus einer Höhenkarte mit optionaler Auflösungsreduzierung."""
    height, width = heightmap.shape

    # Optionales Smoothing für die Höhenkarte
    if smoothing > 1:
        from scipy.ndimage import gaussian_filter
        heightmap = gaussian_filter(heightmap, sigma=smoothing)

    # Auflösung reduzieren
    if resolution > 1:
        new_height = height // resolution
        new_width = width // resolution
        resized_heightmap = np.zeros((new_height, new_width))

        for y in range(new_height):
            for x in range(new_width):
                resized_heightmap[y, x] = heightmap[y * resolution, x * resolution]

        heightmap = resized_heightmap
        height, width = heightmap.shape

    # Vertices und Faces erstellen
    vertices = []
    faces = []

    # X, Y-Koordinaten erstellen
    for y in tqdm(range(height), desc="Erstelle Vertices"):
        for x in range(width):
            z = heightmap[y, x] * scale_z
            # Y-Koordinate wird invertiert, damit das Modell richtig orientiert ist
            vertices.append([x, height - 1 - y, z])

    # Dreiecke erstellen (als Faces)
    for y in tqdm(range(height - 1), desc="Erstelle Faces"):
        for x in range(width - 1):
            # Index der aktuellen Vertex berechnen
            i = y * width + x

            # Zwei Dreiecke erstellen, die ein Quadrat bilden
            faces.append([i, i + 1, i + width])
            faces.append([i + 1, i + width + 1, i + width])

    # Numpy arrays erstellen
    vertices = np.array(vertices)
    faces = np.array(faces)

    # Mesh erstellen
    topo_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))

    # Vertices für jedes Dreieck setzen
    for i, f in enumerate(faces):
        for j in range(3):
            topo_mesh.vectors[i][j] = vertices[f[j]]

    return topo_mesh


def create_output_dir(script_name="topographic-layering"):
    """Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen."""
    output_dir = os.path.join("output", script_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def topographic_layers(image_path, output_path="output.stl", scale_z=10.0, smoothing=1, resolution=1, use_timestamp=False):
    """Haupt-Funktion, die ein JPG in ein 3D-Modell umwandelt."""
    print(f"Verarbeite {image_path}...")

    # Ausgabeverzeichnis erstellen
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    output_dir = create_output_dir(script_name)

    # Zeitstempel einfügen, falls gewünscht
    if use_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        base_name, ext = os.path.splitext(os.path.basename(output_path))
        output_path = f"{base_name}_{timestamp}{ext}"

    # Ausgabepfad anpassen
    if os.path.isabs(output_path):
        # Wenn absoluter Pfad angegeben wurde, behalte den Dateinamen bei
        output_filename = os.path.basename(output_path)
        output_path = os.path.join(output_dir, output_filename)