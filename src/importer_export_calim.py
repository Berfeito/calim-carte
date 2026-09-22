"""Convertit un export brut Calim en data/demande_par_npa.csv.

Usage, depuis la racine du projet :

    python src\\importer_export_calim.py chemin\\vers\\export.xlsx

L'export attendu est une ligne par foyer, avec au minimum les colonnes :
« Nombre de personnes de 14 ans ou plus dans le groupe », « Nombre de personnes
de moins de 14 ans dans le groupe », « Code postal » et « Étiquettes ».

Le script agrege par NPA, en personnes equivalentes, et n'ecrit le fichier
qu'apres avoir affiche un rapport de ce qui entre et de ce qui sort.
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
GEO = RACINE / "geo"
DATA = RACINE / "data"

# --- regles de lecture des etiquettes ---------------------------------------
# Ce sont les seules decisions interpretatives du script. Les changer ici
# change le resultat : toute modification merite d'etre discutee avec la
# coordination avant d'etre appliquee.
ETIQUETTES_MEMBRE = {"Participant Calim 2025", "Participant Calim 2026"}
ETIQUETTES_ATTENTE = {"En liste d'attente"}

# Une personne equivalente = un adulte, ou deux enfants.
POIDS_ENFANT = 0.5

COLONNES = {
    "Nombre de personnes de 14 ans ou plus dans le groupe": "adultes",
    "Nombre de personnes de moins de 14 ans dans le groupe": "enfants",
    "Code postal": "code_postal",
    "Étiquettes": "etiquette",
}


def lire_code_postal(valeur):
    """Rend (genre, code) : suisse et son NPA, etranger, ou manquant.

    L'export contient des codes ecrits de plusieurs facons : « 1201 »,
    « 1201 Genève », et des codes francais a cinq chiffres comme 74000 ou
    01210, pour les foyers de la France voisine. Un code a quatre chiffres
    est suisse, un code a cinq chiffres ne l'est pas.
    """
    if pd.isna(valeur):
        return ("manquant", None)
    chiffres = re.match(r"^\s*(\d+)", str(valeur))
    if not chiffres:
        return ("illisible", None)
    chiffres = chiffres.group(1)
    if len(chiffres) == 4:
        return ("suisse", int(chiffres))
    if len(chiffres) == 5:
        return ("etranger", chiffres)
    return ("illisible", chiffres)


def importer(chemin_export):
    brut = pd.read_excel(chemin_export)
    manquantes = [c for c in COLONNES if c not in brut.columns]
    if manquantes:
        raise ValueError(
            "Colonnes absentes de l'export : "
            + ", ".join(manquantes)
            + "\nColonnes trouvees : "
            + ", ".join(map(str, brut.columns))
        )

    df = brut.rename(columns=COLONNES)
    df["pe"] = df["adultes"].fillna(0) + POIDS_ENFANT * df["enfants"].fillna(0)
    df[["genre", "code"]] = df["code_postal"].apply(
        lambda v: pd.Series(lire_code_postal(v))
    )

    contours = json.loads((GEO / "npa.geojson").read_text(encoding="utf-8"))
    noms_npa = {f["properties"]["npa"]: f["properties"]["nom"] for f in contours["features"]}

    retenus = df[df["etiquette"].isin(ETIQUETTES_MEMBRE | ETIQUETTES_ATTENTE)].copy()
    retenus["statut"] = retenus["etiquette"].apply(
        lambda e: "membre" if e in ETIQUETTES_MEMBRE else "attente"
    )

    # --- rapport ------------------------------------------------------------
    print(f"Export lu : {Path(chemin_export).name}  ({len(df)} lignes)\n")
    print("Etiquettes rencontrees :")
    for etiquette, nombre in df["etiquette"].fillna("(sans etiquette)").value_counts().items():
        sort = "retenue" if etiquette in ETIQUETTES_MEMBRE | ETIQUETTES_ATTENTE else "ignoree"
        print(f"  {str(etiquette)[:34]:36} {nombre:>4} foyers   {sort}")

    print("\nFoyers retenus :")
    for statut in ("membre", "attente"):
        s = retenus[retenus["statut"] == statut]
        dans = s[(s["genre"] == "suisse") & s["code"].isin(noms_npa)]
        hors = s[(s["genre"] == "suisse") & ~s["code"].isin(noms_npa)]
        etr = s[s["genre"] == "etranger"]
        vide = s[s["genre"].isin(["manquant", "illisible"])]
        print(f"  {statut:8} {len(s):>4} foyers, {s['pe'].sum():>7.1f} pers. eq.")
        print(f"           dont dans le canton      {dans['pe'].sum():>7.1f} pers. eq.")
        if len(hors):
            print(f"           suisse hors canton       {hors['pe'].sum():>7.1f} pers. eq."
                  f"  ({', '.join(str(c) for c in sorted(hors['code'].unique()))})")
        if len(etr):
            print(f"           hors de Suisse           {etr['pe'].sum():>7.1f} pers. eq."
                  f"  ({', '.join(sorted(etr['code'].unique()))})")
        if len(vide):
            print(f"           code postal absent       {vide['pe'].sum():>7.1f} pers. eq."
                  f"  ({len(vide)} foyers)")
        zeros = (s["pe"] == 0).sum()
        if zeros:
            print(f"           foyers declares a zero personne : {zeros}")

    # --- agregation ---------------------------------------------------------
    cartographiables = retenus[
        (retenus["genre"] == "suisse") & retenus["code"].isin(noms_npa)
    ]
    table = (
        cartographiables.pivot_table(
            index="code", columns="statut", values="pe", aggfunc="sum"
        )
        .reindex(columns=["membre", "attente"])
        .fillna(0)
    )
    # Tous les NPA du canton figurent dans la sortie, y compris ceux sans
    # demande : la carte doit pouvoir les nommer.
    table = table.reindex(sorted(noms_npa), fill_value=0)
    table.insert(0, "nom", [noms_npa[npa] for npa in table.index])
    table.index.name = "npa"

    sortie = DATA / "demande_par_npa.csv"
    table.to_csv(sortie, encoding="utf-8")

    print(f"\nEcrit : {sortie.relative_to(RACINE)}")
    print(f"  NPA du canton            {len(table):>7}")
    print(f"  NPA porteurs de demande  {(table['membre'] + table['attente'] > 0).sum():>7}")
    print(f"  total membres            {table['membre'].sum():>7.1f} pers. eq.")
    print(f"  total liste d'attente    {table['attente'].sum():>7.1f} pers. eq.")
    print("\nRelancer ensuite :  python src\\construire_carte.py")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    importer(sys.argv[1])
