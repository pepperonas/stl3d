"""
Modul zur Erstellung topografischer 3D-Modelle aus Bildern
"""

import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from stl import mesh
from tqdm import tqdm
from utils.file_utils import ensure_directory_exists

def create_output_dir(script_name="topographic-layering"):
    """
    Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen.
    
    Args:
        script_name: Name des Skripts/Moduls
        
    Returns:
        Pfad zum Ausgabeverzeichnis
    """
    output_dir = os.path.join("output", script_name)
    ensure_directory_exists(output_dir)
    return output_dir

def load_image(image_path):
    """
    Lädt ein Bild und konvertiert es zu Graustufen.
    
    Args:
        image_path: Pfad zum Bild
        
    Returns:
        NumPy-Array des Graustufenbildes
    """
    try:
        img = Image.open(image_path).convert('L')
        return np.array(img)
    except Exception as e:
        raise Exception(f"Fehler beim Laden des Bildes: {e}")

def normalize_heightmap(heightmap):
    """
    Normalisiert die Höhenwerte auf einen Bereich von 0 bis 1.
    
    Args:
        heightmap: 2D-Array der Höhenwerte
        
    Returns:
        Normalisiertes Höhenkarten-Array
    """
    min_val = np.min(heightmap)
    max_val = np.max(heightmap)
    return (heightmap - min_val) / (max_val - min_val)

def create_mesh(heightmap, scale_z=10.0, smoothing=1, resolution=1):
    """
    Erstellt ein 3D-Mesh aus einer Höhenkarte mit optionaler Auflösungsreduzierung.
    
    Args:
        heightmap: 2D-Array der Höhenwerte
        scale_z: Skalierungsfaktor für die Höhe
        smoothing: Stärke der Glättung
        resolution: Faktor zur Reduzierung der Auflösung
        
    Returns:
        mesh.Mesh-Objekt des 3D-Modells
    """
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

def visualize_heightmap(heightmap, output_path):
    """
    Visualisiert die Höhenkarte.
    
    Args:
        heightmap: 2D-Array der Höhenwerte
        output_path: Pfad zum Speichern der Visualisierung
    """
    plt.figure(figsize=(10, 8))
    
    # 3D-Oberfläche erzeugen
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Mesh Grid erstellen
    y, x = np.mgrid[:heightmap.shape[0], :heightmap.shape[1]]
    
    # Oberfläche zeichnen
    surf = ax.plot_surface(x, y, heightmap, cmap='terrain', linewidth=0, antialiased=True)
    
    plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Höhe')
    plt.title('3D-Höhenkarte')
    
    # Visualisierung speichern
    plt.savefig(output_path)
    plt.close()

def topographic_layering_process(image_path, output_path="output.stl", scale_z=10.0, 
                              smoothing=1, resolution=1, use_timestamp=False):
    """
    Hauptfunktion für das Topographic Layering.
    
    Args:
        image_path: Pfad zum Bild
        output_path: Ausgabedatei für das STL-Modell
        scale_z: Skalierungsfaktor für die Höhe
        smoothing: Stärke der Glättung
        resolution: Faktor zur Reduzierung der Auflösung
        use_timestamp: Wenn True, wird der Ausgabedatei ein Zeitstempel hinzugefügt
        
    Returns:
        Der vollständige Pfad zur erstellten STL-Datei
    """
    print(f"Verarbeite {image_path}...")

    # Ausgabeverzeichnis erstellen
    output_dir = create_output_dir()

    # Zeitstempel einfügen, falls gewünscht
    if use_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        base_name, ext = os.path.splitext(os.path.basename(output_path))
        output_path = f"{base_name}_{timestamp}{ext}"

    # Ausgabepfad anpassen
    output_path = os.path.join(output_dir, os.path.basename(output_path))

    # Bild laden
    heightmap = load_image(image_path)

    # Höhenkarte normalisieren
    heightmap = normalize_heightmap(heightmap)

    # Debug-Visualisierung der Höhenkarte speichern
    debug_path = os.path.join(output_dir, os.path.splitext(os.path.basename(output_path))[0] + "_heightmap.png")
    plt.figure(figsize=(10, 8))
    plt.imshow(heightmap, cmap='terrain')
    plt.colorbar(label='Höhe')
    plt.title('Höhenkarte')
    plt.savefig(debug_path)
    plt.close()
    print(f"Höhenkarte gespeichert unter {debug_path}")

    # 3D-Visualisierung der Höhenkarte speichern
    vis_path = os.path.join(output_dir, os.path.splitext(os.path.basename(output_path))[0] + "_3d_preview.png")
    visualize_heightmap(heightmap, vis_path)
    print(f"3D-Vorschau gespeichert unter {vis_path}")

    # Auf der Konsole ein paar Informationen ausgeben
    print(f"Bildgröße: {heightmap.shape[1]}x{heightmap.shape[0]} Pixel")
    print(f"Skalierungsfaktor für die Höhe: {scale_z}")
    print(f"Glättung: {smoothing}")
    print(f"Auflösungsreduzierung: {resolution}")

    # 3D-Mesh erstellen
    print("Erstelle 3D-Mesh...")
    topo_mesh = create_mesh(heightmap, scale_z, smoothing, resolution)

    # STL-Datei speichern
    topo_mesh.save(output_path)
    print(f"3D-Modell gespeichert unter {output_path}")

    return output_path
