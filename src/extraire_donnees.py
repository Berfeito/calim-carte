"""Extrait les donnees de la carte v4 vers geo/ et data/.

Lit source_v4.html (l'ancienne carte, ou toutes les donnees sont enfermees
dans une ligne de JavaScript) et en tire quatre fichiers reutilisables :

    geo/npa.geojson              les 60 polygones de NPA
    geo/eau.geojson              lac, Rhone, Arve
    data/lieux_partenaires.csv   les 23 points de vente
    data/demande_par_npa.csv     membres et liste d'attente par NPA

A lancer depuis la racine du projet :  python src\\extraire_donnees.py
"""

import json
from pathlib import Path

import pandas as pd

# --- emplacements -----------------------------------------------------------
# __file__ est ce script ; .parent est src/ ; .parent.parent est la racine.
# Le script trouve donc ses fichiers quel que soit le dossier d'ou on le lance.
RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "source_v4.html"
GEO = RACINE / "geo"
DATA = RACINE / "data"

PREFIXE = "const DATA = "


def charger_data():
    """Retrouve la ligne 'const DATA = ...' dans le HTML et en rend le JSON."""
    for ligne in SOURCE.read_text(encoding="utf-8").splitlines():
        if ligne.startswith(PREFIXE):
            brut = ligne[len(PREFIXE):].rstrip().rstrip(";")
            return json.loads(brut)
    raise ValueError(f"Ligne '{PREFIXE}' introuvable dans {SOURCE}")


def ecrire_geojson(objet, chemin):
    """Ecrit un objet GeoJSON, accents compris, et annonce ce qui a ete fait."""
    chemin.write_text(json.dumps(objet, ensure_ascii=False), encoding="utf-8")
    print(f"  {chemin.name:26} {len(objet['features']):>4} entites")


def main():
    data = charger_data()
    print(f"Source lue : {SOURCE.name}\n")

    # --- 1. l'eau : recopiee telle quelle -----------------------------------
    print("Geometries :")
    ecrire_geojson(data["water"], GEO / "eau.geojson")

    # --- 2. les polygones de NPA --------------------------------------------
    # On garde la geometrie et quatre proprietes. Les effectifs (membre,
    # attente, total, ratio) partent dans le CSV : ils changeront a chaque
    # export, alors que les contours ne bougeront jamais.
    entites = []
    for f in data["npa"]["features"]:
        p = f["properties"]
        entites.append(
            {
                "type": "Feature",
                "geometry": f["geometry"],
                "properties": {
                    "npa": int(p["npa"]),
                    "nom": p["nom"],
                    "lat": p["lat"],  # centroide, corrige a la main pour le 1247
                    "lon": p["lon"],
                },
            }
        )
    ecrire_geojson(
        {"type": "FeatureCollection", "features": entites},
        GEO / "npa.geojson",
    )

    # --- 3. les lieux partenaires -------------------------------------------
    # Attention : en GeoJSON les coordonnees sont [longitude, latitude].
    # Et le NPA arrive tantot en texte, tantot en nombre : on normalise.
    lieux = []
    for f in data["detaillants"]["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        lieux.append(
            {
                "lieu": p["lieu"],
                "adresse": p.get("adresse", ""),
                "type": p["type"],
                "npa": int(p["npa"]),
                "lat": lat,
                "lon": lon,
            }
        )
    df_lieux = pd.DataFrame(lieux)
    df_lieux.to_csv(DATA / "lieux_partenaires.csv", index=False, encoding="utf-8")

    # --- 4. la demande par NPA ----------------------------------------------
    demande = []
    for f in data["npa"]["features"]:
        p = f["properties"]
        demande.append(
            {
                "npa": int(p["npa"]),
                "nom": p["nom"],
                "membre": p["membre"],
                "attente": p["attente"],
            }
        )
    df_demande = pd.DataFrame(demande)
    df_demande.to_csv(DATA / "demande_par_npa.csv", index=False, encoding="utf-8")

    print("\nTableaux :")
    print(f"  lieux_partenaires.csv      {len(df_lieux):>4} lignes")
    print(f"  demande_par_npa.csv        {len(df_demande):>4} lignes")

    # --- controles ----------------------------------------------------------
    # Ces quatre chiffres sont connus d'avance. S'ils tombent juste,
    # l'extraction est fidele a la source.
    print("\nControles :")
    print(f"  polygones de NPA           {len(entites):>7}   attendu      60")
    print(f"  points de vente            {len(df_lieux):>7}   attendu      23")
    print(f"  total membres              {df_demande['membre'].sum():>7.1f}   attendu   392.5")
    print(f"  total liste d'attente      {df_demande['attente'].sum():>7.1f}   attendu   351.5")


if __name__ == "__main__":
    main()
