"""Construit la carte interactive Calim dans docs/index.html.

Lit les quatre fichiers produits par extraire_donnees.py :

    geo/npa.geojson              contours des 60 NPA
    geo/eau.geojson              lac, Rhone, Arve
    data/lieux_partenaires.csv   les 23 points de vente
    data/demande_par_npa.csv     membres et liste d'attente par NPA

A lancer depuis la racine du projet :  python src\\construire_carte.py
"""

import json
from math import sqrt
from pathlib import Path

import folium
import pandas as pd
from branca.element import MacroElement
from folium.plugins import MarkerCluster
from jinja2 import Template


class EchelleMetrique(MacroElement):
    """Echelle en metres, en bas a droite.

    Celle de Folium affiche aussi les milles et se pose en bas a gauche,
    sous la legende. On la remplace par la notre, rattachee a la carte pour
    que le code s'execute bien apres la creation de celle-ci.
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        L.control.scale({imperial: false, position: 'bottomright'})
            .addTo({{ this._parent.get_name() }});
        {% endmacro %}
        """
    )

RACINE = Path(__file__).resolve().parent.parent
GEO = RACINE / "geo"
DATA = RACINE / "data"
SORTIE = RACINE / "docs" / "index.html"

# --- palette ----------------------------------------------------------------
# Rampe sequentielle a une seule teinte, du clair au fonce : elle se lit par la
# luminosite, donc elle reste ordonnee pour toutes les formes de daltonisme.
# Verifiee avec le validateur de palette (separation CVD et vision normale).
RAMPE = ["#B39BD3", "#8B66B5", "#643F94", "#3B2168"]
SEUILS = [0.25, 0.50, 0.75]  # bornes des quatre classes de part en attente

COULEUR_LIEU = "#00565E"  # points de vente : teal fonce, distinct du violet et de l'eau
TERRE = "#E9E4C4"
BORD_TERRE = "#B7B190"
EAU = "#A9D6E8"
BORD_EAU = "#7FB3CC"
FOND = "#FBF8F0"
ENCRE = "#262620"
GRIS = "#5B5A4E"

RAYON_MAX = 34  # rayon en pixels de la plus grosse bulle


def triangle(largeur=22, nombre=None, couleur=COULEUR_LIEU):
    """Dessine le symbole d'un point de vente.

    Un seul symbole sert a tous les niveaux de zoom : un triangle seul pour
    un lieu unique, le meme triangle portant un chiffre quand plusieurs lieux
    sont regroupes. Le chiffre se loge dans la partie basse, la ou le triangle
    est large. Le lisere blanc detache le symbole du fond.
    """
    h = round(largeur * 0.9)
    texte = ""
    if nombre is not None:
        texte = (
            f'<text x="{largeur / 2:.1f}" y="{h * 0.78:.1f}" text-anchor="middle" '
            f'fill="white" font-family="system-ui, sans-serif" '
            f'font-size="{h * 0.34:.1f}" font-weight="700">{nombre}</text>'
        )
    return (
        f'<svg width="{largeur}" height="{h}" viewBox="0 0 {largeur} {h}" '
        f'style="filter:drop-shadow(0 0 1px rgba(0,0,0,0.55));">'
        f'<polygon points="{largeur / 2:.1f},2 {largeur - 2},{h - 2} 2,{h - 2}" '
        f'fill="{couleur}" stroke="white" stroke-width="2.5" stroke-linejoin="round"/>'
        f"{texte}</svg>"
    )


def couleur_pression(part_attente):
    """Rend le pas de rampe correspondant a la part de liste d'attente."""
    for seuil, couleur in zip(SEUILS, RAMPE):
        if part_attente < seuil:
            return couleur
    return RAMPE[-1]


def charger():
    """Lit les fichiers de donnees et prepare les noms d'affichage."""
    npa = json.loads((GEO / "npa.geojson").read_text(encoding="utf-8"))
    eau = json.loads((GEO / "eau.geojson").read_text(encoding="utf-8"))
    lieux = pd.read_csv(DATA / "lieux_partenaires.csv")
    demande = pd.read_csv(DATA / "demande_par_npa.csv")

    # Dix NPA du centre s'appellent tous « Genève » dans les donnees postales,
    # ce qui rend les bulles indistinguables au clic. data/noms_npa.csv leur
    # donne une appellation courante ; les NPA absents du fichier gardent leur
    # nom d'origine. Corriger un nom se fait dans ce CSV, pas ici.
    noms = pd.read_csv(DATA / "noms_npa.csv").set_index("npa")["nom_affiche"]
    demande["nom"] = demande["npa"].map(noms).fillna(demande["nom"])
    for entite in npa["features"]:
        p = entite["properties"]
        p["nom"] = noms.get(p["npa"], p["nom"])

    demande["total"] = demande["membre"] + demande["attente"]
    # part en attente : indefinie quand il n'y a aucune demande du tout
    demande["part_attente"] = (demande["attente"] / demande["total"]).where(
        demande["total"] > 0
    )
    return npa, eau, lieux, demande


def construire():
    npa, eau, lieux, demande = charger()
    par_npa = demande.set_index("npa").to_dict("index")

    carte = folium.Map(
        tiles=None,  # aucun fond de carte : le canton se suffit a lui-meme
        zoom_control=True,
        control_scale=False,  # on pose notre propre echelle, en metrique seulement
    )
    # Sans fond de carte, Leaflet ignore les bornes de zoom et le regroupement
    # de points refuse de fonctionner ("Map has no maxZoom specified").
    # On les pose donc directement sur la carte.
    carte.options["minZoom"] = 9
    carte.options["maxZoom"] = 16

    style_eau = {"color": BORD_EAU, "weight": 1, "fillColor": EAU, "fillOpacity": 0.9}

    # L'eau est dessinee deux fois, sous puis sur les polygones terrestres :
    # sans cela le chenal du Rhone disparait sous les NPA de la ville.
    folium.GeoJson(eau, style_function=lambda _: style_eau, name="eau (dessous)",
                   control=False).add_to(carte)

    def style_terre(_):
        return {"color": BORD_TERRE, "weight": 0.6, "fillColor": TERRE, "fillOpacity": 1}

    def infobulle_npa(entite):
        p = entite["properties"]
        d = par_npa.get(p["npa"], {})
        membre = d.get("membre", 0)
        attente = d.get("attente", 0)
        total = membre + attente
        part = f"{attente / total:.0%}" if total else "aucune donnée"
        return (
            f"<b>NPA {p['npa']} — {p['nom']}</b><br>"
            f"Membres : {membre:g} pers. éq.<br>"
            f"Liste d'attente : {attente:g} pers. éq.<br>"
            f"Part en attente : {part}"
        )

    for entite in npa["features"]:
        entite["properties"]["infobulle"] = infobulle_npa(entite)

    folium.GeoJson(
        npa,
        style_function=style_terre,
        highlight_function=lambda _: {"weight": 2, "color": ENCRE},
        popup=folium.GeoJsonPopup(fields=["infobulle"], labels=False),
        name="communes (NPA)",
        control=False,
    ).add_to(carte)

    folium.GeoJson(eau, style_function=lambda _: style_eau, name="eau (dessus)",
                   control=False).add_to(carte)

    # --- bulles de demande ---------------------------------------------------
    avec_demande = demande[demande["total"] > 0]
    total_max = avec_demande["total"].max()
    centroides = {
        f["properties"]["npa"]: (f["properties"]["lat"], f["properties"]["lon"])
        for f in npa["features"]
    }

    groupe_bulles = folium.FeatureGroup(name="Demande par NPA", show=True)
    # Les plus grosses d'abord, pour que les petites restent cliquables au-dessus.
    for _, ligne in avec_demande.sort_values("total", ascending=False).iterrows():
        position = centroides.get(ligne["npa"])
        if position is None:
            continue  # NPA present dans les chiffres mais absent des contours
        folium.CircleMarker(
            location=position,
            # rayon proportionnel a la racine carree : c'est l'aire du disque,
            # et non son rayon, qui doit etre proportionnelle a l'effectif
            radius=RAYON_MAX * sqrt(ligne["total"] / total_max),
            color="white",
            weight=1,
            fill=True,
            fill_color=couleur_pression(ligne["part_attente"]),
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>NPA {ligne['npa']:.0f} — {ligne['nom']}</b><br>"
                f"Membres : {ligne['membre']:g} pers. éq.<br>"
                f"Liste d'attente : {ligne['attente']:g} pers. éq.<br>"
                f"Part en attente : {ligne['part_attente']:.0%}",
                max_width=260,
            ),
        ).add_to(groupe_bulles)
    groupe_bulles.add_to(carte)

    # --- points de vente, regroupes ------------------------------------------
    grappes = MarkerCluster(
        name="Points de vente",
        options={
            "maxClusterRadius": 45,
            "spiderfyOnMaxZoom": True,
            "showCoverageOnHover": False,
        },
        # Meme triangle que pour un lieu unique, en plus grand et portant le
        # nombre de lieux regroupes. Ce code s'execute dans le navigateur ;
        # il reproduit la fonction triangle() ci-dessus.
        icon_create_function=f"""
            function(cluster) {{
                var n = cluster.getChildCount();
                var w = n < 10 ? 34 : (n < 100 ? 40 : 46);
                var h = Math.round(w * 0.9);
                var html =
                    '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '"'
                  + ' style="filter:drop-shadow(0 0 1px rgba(0,0,0,0.55));">'
                  + '<polygon points="' + (w / 2) + ',2 ' + (w - 2) + ',' + (h - 2)
                  + ' 2,' + (h - 2) + '" fill="{COULEUR_LIEU}" stroke="white"'
                  + ' stroke-width="2.5" stroke-linejoin="round"/>'
                  + '<text x="' + (w / 2) + '" y="' + (h * 0.78) + '" text-anchor="middle"'
                  + ' fill="white" font-family="system-ui, sans-serif"'
                  + ' font-size="' + (h * 0.34) + '" font-weight="700">' + n + '</text>'
                  + '</svg>';
                return L.divIcon({{
                    html: html, className: '',
                    iconSize: [w, h], iconAnchor: [w / 2, h * 0.64]
                }});
            }}
        """,
    )
    for _, ligne in lieux.iterrows():
        folium.Marker(
            location=(ligne["lat"], ligne["lon"]),
            tooltip=ligne["lieu"],
            popup=folium.Popup(
                f"<b>{ligne['lieu']}</b><br>{ligne['adresse']}<br>"
                f"<i>NPA {ligne['npa']:.0f}</i>",
                max_width=260,
            ),
            icon=folium.DivIcon(
                html=triangle(),
                icon_size=(22, 20),
                icon_anchor=(11, 13),  # centre de gravite du triangle
            ),
        ).add_to(grappes)
    grappes.add_to(carte)

    # --- cadrage sur l'emprise reelle des donnees ----------------------------
    lats = [lat for lat, _ in centroides.values()]
    lons = [lon for _, lon in centroides.values()]
    carte.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20, 20))

    ajouter_habillage(carte, lieux, avec_demande)

    SORTIE.parent.mkdir(exist_ok=True)
    carte.save(str(SORTIE))
    return carte, lieux, demande


def ajouter_habillage(carte, lieux, avec_demande):
    """Titre, legende et mention de source, poses par-dessus la carte."""
    classes = [
        ("moins de 25 %", RAMPE[0]),
        ("25 à 50 %", RAMPE[1]),
        ("50 à 75 %", RAMPE[2]),
        ("75 % et plus", RAMPE[3]),
    ]
    lignes_legende = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
        f'<span style="width:14px;height:14px;border-radius:50%;background:{c};'
        f'border:1px solid white;box-shadow:0 0 0 1px #999;"></span>{nom}</div>'
        for nom, c in classes
    )

    html = f"""
    <style>
      html, body {{ background: {FOND}; }}
      /* le fond du conteneur Leaflet, visible autour du canton */
      .leaflet-container {{ background: {FOND} !important; }}
      .habillage {{
        position: absolute; z-index: 1000;
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        background: rgba(251,248,240,0.94); border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.18);
      }}
      #titre {{ top: 12px; left: 56px; padding: 6px 12px;
                font-size: 1.15rem; font-weight: 700; color: {ENCRE}; }}
      #soustitre {{ top: 52px; left: 56px; padding: 3px 10px;
                    font-size: 0.8rem; color: {GRIS}; }}
      #legende {{ bottom: 16px; left: 12px; padding: 8px 14px;
                  font-size: 0.78rem; color: {ENCRE}; max-width: 245px; }}
      #legende h4 {{ margin: 0 0 5px 0; font-size: 0.8rem; }}
      #legende summary {{ cursor: pointer; font-weight: 700; font-size: 0.8rem;
                          list-style: none; }}
      #legende summary::-webkit-details-marker {{ display: none; }}
      #legende summary::after {{ content: " ▾"; color: {GRIS}; }}
      #legende[open] summary::after {{ content: " ▴"; }}
      #source {{ top: 12px; right: 12px; padding: 4px 10px;
                 font-size: 0.7rem; color: {GRIS}; }}
      /* l'echelle de Leaflet, en bas a droite, degagee de la legende */
      .leaflet-bottom.leaflet-right .leaflet-control-scale {{ margin-bottom: 16px; }}
      @media (max-width: 640px) {{
        #titre {{ font-size: 0.95rem; left: 56px; right: 12px; }}
        #soustitre {{ display: none; }}
        #source {{ font-size: 0.62rem; top: auto; bottom: 16px; right: 12px; }}
        #legende {{ font-size: 0.72rem; padding: 7px 10px; max-width: 168px; }}
        #legende .aide {{ display: none; }}
      }}
    </style>
    <div class="habillage" id="titre">Calim — points de vente et pression sur l'accès</div>
    <div class="habillage" id="soustitre">Survolez un point pour son nom · cliquez sur un point ou une bulle pour le détail</div>
    <details class="habillage" id="legende" open>
      <summary>Légende</summary>
      <h4 style="margin-top:8px;">Points de vente</h4>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0;">
        <span style="flex:none;line-height:0;">{triangle()}</span>
        {len(lieux)} points de vente
      </div>
      <h4 style="margin-top:10px;">Demande par NPA</h4>
      <div style="font-size:0.75rem;">Taille = demande totale (pers. éq.)</div>
      <div style="font-size:0.75rem;margin:4px 0 2px;">Couleur = part de la liste d'attente</div>
      {lignes_legende}
      <div class="aide" style="font-size:0.7rem;color:{GRIS};margin-top:6px;">
        {len(avec_demande)} NPA sur 60 portent de la demande.
      </div>
    </details>
        <div class="habillage" id="source">Données Calim · contours SITG, extraction 13.07.2026, reprojetés et simplifiés</div>
    """
    carte.get_root().html.add_child(folium.Element(html))

    carte.add_child(EchelleMetrique())


if __name__ == "__main__":
    carte, lieux, demande = construire()
    print(f"Carte ecrite : {SORTIE.relative_to(RACINE)}")
    print(f"  points de vente        {len(lieux):>4}")
    print(f"  NPA avec demande       {(demande['membre'] + demande['attente'] > 0).sum():>4} sur {len(demande)}")
    print(f"  total membres          {demande['membre'].sum():>7.1f}")
    print(f"  total liste d'attente  {demande['attente'].sum():>7.1f}")
