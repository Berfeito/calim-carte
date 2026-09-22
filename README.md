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
en fin d'exécution quatre chiffres de contrôle : nombre de points de vente, nombre de NPA
porteurs de demande, total des membres et total de la liste d'attente. Ces chiffres doivent
correspondre à ceux qu'annonce le script d'import lors de la dernière mise à jour des
données ; tout écart signale une altération en cours de route.

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
  importer_export_calim.py conversion d'un export Calim vers demande_par_npa.csv
  construire_carte.py      construction de la carte — le script à relancer
  extraire_donnees.py      extraction unique depuis l'ancienne carte (voir Historique)
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

**Nouvel export de membres et de liste d'attente.** L'export attendu est une ligne par
foyer, avec les colonnes « Nombre de personnes de 14 ans ou plus dans le groupe »,
« Nombre de personnes de moins de 14 ans dans le groupe », « Code postal » et
« Étiquettes ».

```powershell
python src\importer_export_calim.py chemin\vers\export.xlsx
python src\construire_carte.py
```

Le script d'import affiche un rapport avant d'écrire : étiquettes rencontrées et sort
réservé à chacune, foyers retenus, et ce qui sort de la carte — foyers hors canton, hors de
Suisse, sans code postal, ou déclarés à zéro personne. **Lire ce rapport fait partie de la
mise à jour** : c'est le seul endroit où apparaît ce que la carte ne montre pas.

Si l'export comporte une étiquette inconnue, elle sera ignorée et signalée comme telle dans
le rapport. Les règles de lecture des étiquettes sont en tête de
`src/importer_export_calim.py`.

**Autre modification** — appellations de quartiers, lieux partenaires : éditer le fichier
concerné dans `data/`, directement sur github.com avec le crayon ou localement, puis
relancer `python src\construire_carte.py`.

Dans les deux cas, terminer par `git add .`, `git commit -m "..."`, `git push`. Le site se
met à jour automatiquement dans la minute qui suit.

Un NPA absent de `data/noms_npa.csv` garde son nom postal d'origine.

---

## Provenance des données

**Effectifs de membres et de liste d'attente** — export interne Calim
(`2026.09.21stat_membres2.xlsx`), extraction du 21 septembre 2026, transmise par la
coordination. Il n'existe aucun mécanisme de mise à jour automatique ; toute actualisation
passe par un nouvel export et par `src/importer_export_calim.py`.

Une personne équivalente vaut un adulte, ou deux enfants. L'export distingue les personnes
de 14 ans ou plus de celles de moins de 14 ans.

**Lieux partenaires** — relevés à l'origine sur `calim-ge.ch/les-lieux-ou-depenser-vos-radis`.

**Contours des NPA, du lac et des rivières** — SITG, couches `GEO_POSTE_PL`,
`GEO_LAC_LEMAN` et `CAD_COMMUNE`, extraction du 13 juillet 2026.

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
appellation courante. Les noms des NPA 1201 à 1209 ont été fournis par la coordination
Calim le 22 septembre 2026 et font foi. Celui du 1215 reste une proposition.
**Un code postal n'est pas un quartier** : les deux découpages ne coïncident pas. Ces noms
sont des repères de lecture, pas des définitions.

**Étiquettes comptées comme membres.** L'export ne porte pas de champ de statut : le statut
se lit dans la colonne « Étiquettes ». Sont comptés comme membres « Participant Calim 2025 »
et « Participant Calim 2026 » ; comme liste d'attente « En liste d'attente ». Les étiquettes
de groupes locaux (Glo Jonx, Glo Meyrin, Glo Pâquis — 22 foyers, 10 personnes équivalentes),
« Membre asso », « Résiliation Calim », « Calim ADMIN », « Coordination » et
« Technique - ne pas supprimer » sont écartées. Une ligne ne portant qu'une étiquette, un
foyer membre également rattaché à un groupe local n'apparaît pas dans le décompte des
membres. Ce point est à confirmer avec la coordination.

---

## Limites connues

**Le regroupement des points de vente se fait par proximité à l'écran, non par NPA.** Au
centre-ville, un même symbole peut agréger des lieux relevant des NPA 1201, 1204 et 1205.
Un regroupement strictement par code postal est réalisable — chaque lieu porte son NPA dans
`lieux_partenaires.csv` — mais demanderait d'écrire la bascule entre les deux vues. Choix
assumé en l'état.

**Vingt-et-un NPA n'ont aucune donnée de demande** et ne portent donc pas de bulle. La carte
ne permet pas de distinguer une absence de donnée d'une demande réellement nulle.

**Cent vingt-huit foyers étiquetés déclarent zéro personne** dans l'export du 21 septembre
2026. Ils comptent pour zéro personne équivalente : les totaux affichés sont donc des
minorants.

**Les foyers hors du canton sortent de la carte** : 11,5 personnes équivalentes de membres
et 5,0 de liste d'attente dans l'export du 21 septembre 2026, réparties entre la France
voisine — Ferney-Voltaire, Prévessin, Annemasse — et d'autres cantons. Le rapport du script
d'import les chiffre à chaque mise à jour.

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
