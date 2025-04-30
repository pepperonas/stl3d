"""
Modul zur Erstellung von 3D-Modellen aus Höhenlinien eines Bildes
"""

import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from PIL import Image
from stl import mesh
import cv2
from scipy.ndimage import gaussian_filter
from tqdm import tqdm
from utils.file_utils import ensure_directory_exists

def create_output_dir(script_name="contour-crafting"):
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

def extract_contours(heightmap, num_contours=10, smoothing=1, invert=False, is_photo=False):
    """
    Extrahiert Höhenlinien aus der Höhenkarte.
    
    Args:
        heightmap: 2D-Array der Höhenwerte
        num_contours: Anzahl der zu extrahierenden Höhenlinien
        smoothing: Stärke der Glättung
        invert: Wenn True, wird das Bild invertiert
        is_photo: Wenn True, wird der Foto-Modus aktiviert
        
    Returns:
        Tupel (contours, heights) der extrahierten Konturen und zugehörigen Höhen
    """
    original_heightmap = heightmap.copy()

    # Bild bei Bedarf invertieren
    if invert:
        heightmap = 1.0 - heightmap

    # Glätten, wenn erforderlich
    if smoothing > 1:
        heightmap = gaussian_filter(heightmap, sigma=smoothing)

    # Bei Fotos: Vorverarbeitung für bessere Konturen
    if is_photo:
        # Kontrast erhöhen
        heightmap = np.clip((heightmap - 0.5) * 1.5 + 0.5, 0, 1)

        # Kantenfilter anwenden für bessere Konturen
        edges = cv2.Canny((heightmap * 255).astype(np.uint8), 30, 100)

        # Erweitern der Kanten für bessere Erkennung
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Debug-Visualisierung der Kanten
        plt.figure(figsize=(12, 10))
        plt.imshow(edges, cmap='gray')
        plt.title('Kantenerkennung für Konturen')
        plt.savefig("edges_debug.png")
        plt.close()

        # Mit Canny gefundene Kanten in ein Bild umwandeln
        edge_heightmap = edges.astype(float) / 255.0

        # Sobel-Filter für graduelle Übergänge
        sobelx = cv2.Sobel(heightmap, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(heightmap, cv2.CV_64F, 0, 1, ksize=3)
        sobel = np.sqrt(sobelx ** 2 + sobely ** 2)
        sobel = sobel / np.max(sobel)  # Normalisieren

        # Kombinieren von Kanten und Gradienten
        heightmap = 0.7 * sobel + 0.3 * edge_heightmap

    # Höhenkarte in ein Format konvertieren, das OpenCV verarbeiten kann
    img_uint8 = (heightmap * 255).astype(np.uint8)

    # Konturen für Fotos extrahieren
    if is_photo:
        contours_all = []
        heights = []

        # Mehrere Schwellenwerte für Foto ausprobieren
        thresholds = np.linspace(50, 200, num_contours)

        for i, threshold in enumerate(thresholds):
            # Binary Threshold anwenden
            _, binary = cv2.threshold(img_uint8, threshold, 255, cv2.THRESH_BINARY)

            # Morphologische Operationen zur Verbesserung der Konturen
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # Konturen finden
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # Filtern nach Konturlänge und Fläche
                area = cv2.contourArea(contour)
                if len(contour) >= 5 and area > 100 and area < 0.5 * img_uint8.shape[0] * img_uint8.shape[1]:
                    # Konturen vereinfachen, um die Anzahl der Punkte zu reduzieren
                    epsilon = 0.002 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)

                    # Nur gleichmäßig verteilte Konturen hinzufügen
                    if i % 2 == 0 or len(contours_all) < 5:
                        contours_all.append(approx)
                        heights.append((i + 1) / len(thresholds))

        print(f"Photo-Modus ergab {len(contours_all)} Konturen")

        # Wenn genügend Konturen gefunden wurden, verwende diese
        if len(contours_all) >= 3:
            return contours_all, heights

    # Adaptiven Threshold probieren
    adaptive_threshold = cv2.adaptiveThreshold(
        img_uint8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Konturen extrahieren
    contours, _ = cv2.findContours(adaptive_threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Filtern nach Größe
    filtered_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100 and area < img_uint8.shape[0] * img_uint8.shape[1] * 0.9:
            filtered_contours.append(contour)

    print(f"Adaptiver Threshold ergab {len(filtered_contours)} Konturen")

    contours_all = []
    heights = []

    if len(filtered_contours) >= 3:
        # Verwende die gefilterten Konturen
        for i, contour in enumerate(filtered_contours):
            if len(contour) >= 5:
                contours_all.append(contour)
                # Höhe basierend auf Position im Array
                heights.append((i + 1) / len(filtered_contours))

        return contours_all, heights

    # Fallback: Original-Methode mit mehreren Schwellenwerten
    print("Verwende Fallback-Methode mit mehreren Schwellenwerten")
    
    min_val = np.min(heightmap)
    max_val = np.max(heightmap)
    step = (max_val - min_val) / num_contours
    levels = np.arange(min_val + step, max_val, step)
    
    for i, level in enumerate(levels):
        # Schwellenwert für diese Höhe
        threshold = int(((level - min_val) / (max_val - min_val)) * 255)
        _, binary = cv2.threshold(img_uint8, threshold, 255, cv2.THRESH_BINARY)

        # Konturen finden
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Nur Konturen mit ausreichender Länge hinzufügen
        for contour in contours:
            if len(contour) >= 5:  # Mindestens 5 Punkte für eine sinnvolle Kontur
                # Konturen vereinfachen
                epsilon = 0.01 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                contours_all.append(approx)
                heights.append((i + 1) * step)  # Höhe dieser Kontur

    return contours_all, heights

def create_contour_mesh(contours, heights, image_shape, extrusion_height=1.0, base_height=0.5):
    """
    Erstellt ein 3D-Mesh aus den Höhenlinien.
    
    Args:
        contours: Liste der Konturen
        heights: Liste der Höhenwerte für jede Kontur
        image_shape: Tupel (height, width) der Bildgröße
        extrusion_height: Skalierungsfaktor für die Höhe
        base_height: Höhe der Basisebene
        
    Returns:
        mesh.Mesh-Objekt des 3D-Modells
    """
    height, width = image_shape

    vertices = []
    faces = []
    vertex_count = 0

    # Basisfläche erstellen (optional)
    base_vertices = [
        [0, 0, 0],
        [width, 0, 0],
        [width, height, 0],
        [0, height, 0]
    ]

    for v in base_vertices:
        vertices.append(v)

    # Basisfläche aus zwei Dreiecken
    faces.append([0, 1, 2])
    faces.append([0, 2, 3])
    vertex_count = 4

    # Für jede Kontur
    for i, (contour, contour_height) in enumerate(tqdm(zip(contours, heights),
                                                    desc="Erstelle 3D-Konturen",
                                                    total=len(contours))):
        # Z-Höhe für diese Kontur
        z = contour_height * extrusion_height + base_height

        # Anzahl der Punkte in dieser Kontur
        n_points = len(contour)

        if n_points < 3:
            continue  # Überspringe zu kleine Konturen

        # Für jeden Punkt in der Kontur
        contour_start_idx = vertex_count

        for point in contour:
            # Punkt umkehren, damit y-Achse richtig orientiert ist
            x, y = point[0][0], height - point[0][1]
            vertices.append([x, y, z])
            vertex_count += 1

        # Verbinde Punkte, um Flächen zu erstellen
        for j in range(n_points):
            # Verwende Dreiecke zwischen benachbarten Punkten
            idx1 = contour_start_idx + j
            idx2 = contour_start_idx + (j + 1) % n_points

            # Füge Dreieck hinzu (gegen den Uhrzeigersinn für korrekte Normalen)
            faces.append([idx1, idx2, contour_start_idx])

    vertices = np.array(vertices)
    faces = np.array(faces)

    # Mesh erstellen
    contour_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))

    # Vertices für jedes Dreieck setzen
    for i, f in enumerate(faces):
        for j in range(3):
            contour_mesh.vectors[i][j] = vertices[f[j]]

    return contour_mesh

def visualize_contours(heightmap, contours, output_path):
    """
    Visualisiert die extrahierten Höhenlinien.
    
    Args:
        heightmap: 2D-Array der Höhenwerte
        contours: Liste der Konturen
        output_path: Pfad zum Speichern der Visualisierung
    """
    plt.figure(figsize=(12, 10))

    # Höhenkarte als Hintergrund anzeigen
    plt.imshow(heightmap, cmap='terrain', alpha=0.7)

    # Konturen in verschiedenen Farben darstellen
    colors = cm.rainbow(np.linspace(0, 1, len(contours)))

    for i, contour in enumerate(contours):
        # Kontur in eine Liste von (x,y)-Koordinaten umwandeln
        contour_reshaped = contour.reshape(-1, 2)
        plt.plot(contour_reshaped[:, 0], contour_reshaped[:, 1], color=colors[i % len(colors)], linewidth=1.5)

    plt.colorbar(label='Höhe')
    plt.title('Extrahierte Höhenlinien')
    plt.axis('equal')

    # Visualisierung speichern
    plt.savefig(output_path)
    plt.close()

def contour_crafting_process(image_path, output_path="output_contour.stl", num_contours=10,
                        extrusion_height=1.0, base_height=0.5, smoothing=1, invert=False, 
                        is_photo=False, use_timestamp=False):
    """
    Hauptfunktion für das Contour Crafting.
    
    Args:
        image_path: Pfad zum Bild
        output_path: Ausgabedatei für das STL-Modell
        num_contours: Anzahl der zu extrahierenden Höhenlinien
        extrusion_height: Höhe der Extrusion für die Höhenlinien
        base_height: Höhe der Basisebene
        smoothing: Stärke der Glättung (1 = keine Glättung)
        invert: Wenn True, wird das Bild invertiert
        is_photo: Wenn True, wird der Foto-Modus aktiviert
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
    plt.figure(figsize=(12, 10))
    plt.imshow(heightmap, cmap='gray')
    plt.colorbar(label='Höhenwerte')
    plt.title('Originale Höhenkarte')
    debug_path = os.path.join(output_dir, os.path.splitext(os.path.basename(output_path))[0] + "_original.png")
    plt.savefig(debug_path)
    plt.close()
    print(f"Originale Höhenkarte gespeichert unter {debug_path}")

    # Höhenlinien extrahieren
    print("Extrahiere Höhenlinien...")
    contours, heights = extract_contours(heightmap, num_contours, smoothing, invert, is_photo)
    print(f"{len(contours)} Höhenlinien extrahiert.")

    # Visualisierung der Höhenlinien
    vis_path = os.path.join(output_dir, os.path.splitext(os.path.basename(output_path))[0] + "_contours.png")
    visualize_contours(heightmap, contours, vis_path)
    print(f"Höhenlinien-Visualisierung gespeichert unter {vis_path}")

    # 3D-Mesh erstellen
    print("Erstelle 3D-Mesh aus Höhenlinien...")
    contour_mesh = create_contour_mesh(contours, heights, heightmap.shape,
                                    extrusion_height, base_height)

    # STL-Datei speichern
    contour_mesh.save(output_path)
    print(f"3D-Modell gespeichert unter {output_path}")

    return output_path
