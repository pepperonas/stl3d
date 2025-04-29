#!/usr/bin/env python3
# Contour Crafting Tool
# Erstellt ein 3D-Modell aus einem Bild mittels Höhenlinien

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from PIL import Image
from stl import mesh
import argparse
import os
import sys
import datetime
from tqdm import tqdm
import cv2
from scipy.ndimage import gaussian_filter


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


def extract_contours(heightmap, num_contours=10, smoothing=1, invert=False, is_photo=False):
    """Extrahiert Höhenlinien aus der Höhenkarte."""
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

        # Wir können auch Sobel-Filter verwenden für graduelle Übergänge
        sobelx = cv2.Sobel(heightmap, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(heightmap, cv2.CV_64F, 0, 1, ksize=3)
        sobel = np.sqrt(sobelx ** 2 + sobely ** 2)
        sobel = sobel / np.max(sobel)  # Normalisieren

        # Kombinieren von Kanten und Gradienten
        heightmap = 0.7 * sobel + 0.3 * edge_heightmap

        # Debug-Visualisierung des kombinierten Ergebnisses
        plt.figure(figsize=(12, 10))
        plt.imshow(heightmap, cmap='viridis')
        plt.colorbar(label='Höhenwerte')
        plt.title('Kombinierte Kanten und Gradienten')
        plt.savefig("combined_edges_debug.png")
        plt.close()

    # Werte für Höhenlinien berechnen
    min_val = np.min(heightmap)
    max_val = np.max(heightmap)

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

    # Standard-Methode mit adaptivem Threshold für schwierige Bilder
    step = (max_val - min_val) / num_contours
    levels = np.arange(min_val + step, max_val, step)

    # OpenCV verwenden, um Höhenlinien zu extrahieren
    contours_all = []
    heights = []

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
    """Erstellt ein 3D-Mesh aus den Höhenlinien."""
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
    """Visualisiert die extrahierten Höhenlinien."""
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


def create_output_dir(script_name="contour-crafting"):
    """Erstellt das Ausgabeverzeichnis basierend auf dem Skriptnamen."""
    output_dir = os.path.join("output", script_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def contour_crafting(image_path, output_path="output_contour.stl", num_contours=10,
                     extrusion_height=1.0, base_height=0.5, smoothing=1, invert=False, is_photo=False,
                     use_timestamp=False):
    """Haupt-Funktion für das Contour Crafting."""
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
    else:
        # Wenn relativer Pfad angegeben wurde
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


def main():
    parser = argparse.ArgumentParser(description='Erstellt ein 3D-Modell aus Höhenlinien eines Bildes.')
    parser.add_argument('image_path', help='Pfad zum Bild')
    parser.add_argument('-o', '--output', default='output_contour.stl',
                        help='Ausgabepfad für die STL-Datei')
    parser.add_argument('-n', '--num-contours', type=int, default=10,
                        help='Anzahl der Höhenlinien')
    parser.add_argument('-e', '--extrusion-height', type=float, default=1.0,
                        help='Extrusionshöhe für die Höhenlinien')
    parser.add_argument('-b', '--base-height', type=float, default=0.5,
                        help='Höhe der Basisebene')
    parser.add_argument('-s', '--smoothing', type=float, default=1.0,
                        help='Glättungsfaktor (1 = keine Glättung)')
    parser.add_argument('-i', '--invert', action='store_true',
                        help='Invertiert das Bild (Schwarz wird zu Weiß)')
    parser.add_argument('-p', '--photo', action='store_true',
                        help='Aktiviert den Foto-Modus für reale Bilder')
    parser.add_argument('-t', '--timestamp', action='store_true',
                        help='Zeitstempel (yyyy-MM-dd-HH-mm-ss) an Ausgabedatei anfügen')

    args = parser.parse_args()

    try:
        contour_crafting(args.image_path, args.output, args.num_contours,
                         args.extrusion_height, args.base_height, args.smoothing,
                         args.invert, args.photo, args.timestamp)
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())