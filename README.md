# Calim — points de vente et pression sur l'accès

Carte interactive du canton de Genève montrant, par numéro postal d'acheminement (NPA),
l'écart entre l'offre — les lieux où dépenser ses radis — et la demande — les membres
inscrits et les foyers en liste d'attente.

**Carte en ligne : https://berfeito.github.io/calim-carte/**

La Calim (Caisse genevoise de l'alimentation) est une coopérative genevoise de démocratie
alimentaire fonctionnant avec une monnaie interne, le radis. Cette carte sert d'appui aux
démarches auprès des communes et des bailleurs, et de support de discussion en séance du
groupe de travail Finances.

---

## Ce que la carte montre

| Élément | Encodage |
|---|---|
| Point de vente | triangle teal ; le chiffre indique le nombre de points regroupés à ce niveau de zoom |
| Bulle par NPA | **taille** = demande totale (membres + attente, en personnes équivalentes) ; l'aire est proportionnelle à l'effectif, donc le rayon suit la racine carrée |
| Bulle par NPA | **couleur** = part de la liste d'attente, en quatre classes |
| Lac, Rhône, Arve | polygones bleus |

La rampe de couleur des bulles est d'une seule teinte, du violet clair au violet foncé.
Ce choix est délibéré : elle se lit par la luminosité, un canal que toutes les formes de
daltonisme conservent. Le dégradé vert-jaune-rouge de la version précédente ne remplissait
pas cette condition. Les triangles ajoutent un second canal, la forme, de sorte que la
distinction entre offre et demande survit à une impression en noir et blanc.

---

## Reconstruire la carte

Prérequis : Python 3.11 ou plus récent, et git.

```powershell
git clone https://github.com/Berfeito/calim-carte.git
cd calim-carte
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\construire_carte.py
```

Sous macOS ou Linux, l'activation s'écrit `source .venv/bin/activate` et les chemins
utilisent des barres obliques.

Le script lit les fichiers de `geo/` et `data/`, puis réécrit `docs/index.html`. Il affiche
en fin d'exécution quatre chiffres de contrôle — 23 points de vente, 39 NPA porteurs de
demande sur 60, 392,5 membres et 351,5 personnes en attente. Un écart sur l'un de ces
chiffres signale une altération des données d'entrée.

---

## Structure du dépôt

```
data/
  lieux_partenaires.csv    les 23 points de vente : nom, adresse, type, NPA, coordonnées
  demande_par_npa.csv      membres et liste d'attente par NPA, en personnes équivalentes
  noms_npa.csv             appellations d'affichage des NPA du centre-ville
geo/
  npa.geojson              contours des 60 NPA du canton, en WGS84
  eau.geojson              lac Léman, Rhône, Arve
src/
  extraire_donnees.py      extraction unique depuis l'ancienne carte (voir Historique)
  construire_carte.py      construction de la carte — le script à relancer
docs/
  index.html               la carte, publiée par GitHub Pages
```

Le principe est la séparation des données et du code. Les contours ne changeront
pratiquement jamais ; les effectifs changeront à chaque export. Une mise à jour touche donc
un fichier de quelques kilooctets, dont le `git diff` montre exactement ce qui a bougé, au
lieu d'un fichier de géométries où le changement serait noyé.

`docs/index.html` est un produit du script, jamais un fichier à retoucher à la main : toute
modification y serait effacée à la reconstruction suivante.

---

## Mettre à jour les données

1. Modifier le fichier concerné dans `data/` — directement sur github.com, avec le crayon,
   ou localement dans un éditeur.
2. Relancer `python src\construire_carte.py`.
3. Vérifier les quatre chiffres de contrôle.
4. `git add .`, `git commit -m "..."`, `git push`.

Le site se met à jour automatiquement dans la minute qui suit.

Les appellations de quartiers se corrigent dans `data/noms_npa.csv`, sans toucher au code.
Un NPA absent de ce fichier garde son nom postal d'origine.

---

## Provenance des données

**Effectifs de membres et de liste d'attente** — export interne Calim
(`Vis_detaillants_membres_attents.xlsx`). Date d'extraction : 13 juillet 2026. Il n'existe
aucun mécanisme de mise à jour automatique ; toute actualisation passe par un nouvel export.

**Lieux partenaires** — relevés à l'origine sur `calim-ge.ch/les-lieux-ou-depenser-vos-radis`.

**Contours des NPA, du lac et des rivières** — SITG, couches `GEO_POSTE_PL`,
`GEO_LAC_LEMAN` et `CAD_COMMUNE`. Date d'extraction : 13 juillet 2026

Traitements appliqués aux données SITG : reprojection d'EPSG:2056 (CH1903+/LV95) vers
EPSG:4326 (WGS84), union des polygones par NPA, calcul des centroïdes, simplification des
contours, et découpe du lac et des rivières sur l'emprise du canton.

Les conditions d'utilisation du SITG imposent d'indiquer la source, la date d'extraction et
les traitements appliqués. Le niveau de diffusion doit être vérifié couche par couche dans
le catalogue SITG : le niveau A autorise la réutilisation, y compris commerciale, tandis que
le niveau A\* exige une autorisation préalable. Voir
https://sitg.ge.ch/ressources/conditions-utilisation-donnees

---

## Décisions de publication

**Agrégats par NPA publiés en l'état.** Le dépôt est public, condition nécessaire à la
publication par GitHub Pages sur un compte gratuit. Les effectifs par NPA y sont donc
visibles de tous. Plusieurs NPA ruraux ne comptent qu'une seule personne équivalente, ce qui
rend l'information théoriquement rapprochable d'un individu dans une petite commune. La
décision de publier néanmoins, au motif que l'agrégat par NPA est suffisamment anonyme, a
été prise le 20 septembre 2026. L'alternative écartée consistait à regrouper les NPA sous
cinq personnes dans une catégorie « moins de 5 ».

Cette décision se réexamine si la granularité descend un jour sous le NPA, ou si les
effectifs deviennent nominatifs.

**Appellations de quartiers.** La Poste nomme « Genève » dix zones postales du centre, ce
qui rendait dix bulles indistinguables au clic. `data/noms_npa.csv` leur attribue une
appellation courante. Quatre de ces noms sont recoupés par les adresses des partenaires —
Grottes en 1201, Rive en 1204, Plainpalais en 1205, Budé en 1209 — les six autres reposent
sur l'usage. **Un code postal n'est pas un quartier** : les deux découpages ne coïncident
pas. Ces noms sont des repères de lecture, pas des définitions.

---

## Limites connues

**Le regroupement des points de vente se fait par proximité à l'écran, non par NPA.** Au
centre-ville, un même symbole peut agréger des lieux relevant des NPA 1201, 1204 et 1205.
Un regroupement strictement par code postal est réalisable — chaque lieu porte son NPA dans
`lieux_partenaires.csv` — mais demanderait d'écrire la bascule entre les deux vues. Choix
assumé en l'état.

**Vingt-et-un NPA n'ont aucune donnée de demande** et ne portent donc pas de bulle. La carte
ne permet pas de distinguer une absence de donnée d'une demande réellement nulle.

**Un point de vente est situé hors du canton**, au NPA 1295 (Mies, Vaud) : La Ferme du Torry
en vente directe. Son triangle s'affiche mais il n'appartient à aucun polygone de la carte.

**Les producteurs partageant un même marché portent un décalage artificiel** de 0,00028
degré, hérité de la version précédente, où il évitait que les points se recouvrent. Le
regroupement automatique rend ce décalage inutile ; il n'a pas encore été retiré. Les
coordonnées concernées sont donc décalées d'une trentaine de mètres par rapport au marché
réel — sans effet visible à l'échelle de la carte.

---

## Historique

Cette carte succède à une page HTML autonome de 415 Ko dans laquelle données et code étaient
mêlés, et qui ne pouvait être partagée qu'en pièce jointe. `src/extraire_donnees.py` a servi
une seule fois, à extraire les données de cette page ; il n'a plus d'utilité courante et est
conservé pour mémoire. La page d'origine n'est pas versionnée ici.

---

## Licence

Le code est publié sous licence MIT (voir `LICENSE`).

Cette licence ne couvre pas les données. Les contours géographiques relèvent des conditions
du SITG rappelées plus haut ; les effectifs de membres et de liste d'attente appartiennent à
la Calim.
