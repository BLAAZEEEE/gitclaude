---
name: simplifie
description: Rédige ou réécrit des documents de projet (BTS SIO, AP, Scrum, Product Backlog, Definition of Done, planning de sprints, expression de besoin, compte rendu, fiche de recette, cahier des charges…) de façon simple, en ne gardant que ce que la consigne demande. Utilise ce skill dès que l'utilisateur tape /simplifie, dit « fais simple », « simplifie », « juste l'essentiel », « que ce qui est demandé », « pas de truc en plus », trouve un document trop long ou trop chargé, ou demande de rédiger un livrable scolaire à partir d'un sujet, d'un ordre du jour ou d'une fiche mission — même s'il ne prononce pas le mot « simplifier ».
---

# Simplifie

Le but : un document que l'utilisateur peut rendre tel quel. **Tout ce que la consigne exige, rien d'autre.**

Pourquoi c'est important : l'évaluateur vérifie la consigne point par point. Ce qui dépasse ne rapporte rien, noie l'essentiel, allonge la relecture, expose à des questions sur des choses non demandées et crée des incohérences à maintenir entre documents.

## 1. Lire la consigne avant d'écrire

- Chercher les sources dans le dossier : sujet, fiche mission, ordre du jour, document de contexte. Pour un `.docx` ou un `.pdf`, en extraire le texte.
- Dresser la liste exacte de ce qui est demandé pour **ce** document : rubriques, livrables, contraintes nommées (versions, VLAN, langue, format…).
- Réutiliser ce que les sources donnent déjà — acteurs, organigramme, profils, règles métier — plutôt que de le redemander à l'utilisateur.

## 2. Écrire le minimum complet

**Garder :**
- chaque élément explicitement demandé ;
- les contraintes que la consigne impose, même transverses (ex. RGPD, droits d'accès par profil) ;
- les décisions prises par l'utilisateur dans la conversation.

**Retirer, sauf si la consigne le demande :** estimations et points, analyses de risques, jalons, ordres de priorité de secours, journaux de décisions, questions ouvertes, annexes, conseils de méthode, paragraphes « pourquoi », détails des étapes ou missions futures.

Quand la consigne laisse un choix (« MoSCoW **ou** valeur métier »), n'en appliquer qu'un.

Test pour chaque section : *la consigne le demande-t-elle, ou l'utilisateur l'a-t-il demandé ?* Sinon, supprimer.

## 3. Style

- Français simple, phrases courtes.
- Garder le vocabulaire du sujet : s'il dit « recette », ne pas écrire « pré-prod ».
- Tableaux courts et listes plutôt que paragraphes. Un critère = une ligne.
- Titres qui reprennent les intitulés de la consigne, pour que l'évaluateur retrouve chaque point.
- Pas d'introduction ni de conclusion décoratives, pas d'emojis.
- Une page si le contenu demandé le permet.

**Exemple — Definition of Done**

Trop chargé : 20 critères numérotés D1 à D20 répartis en 6 blocs, une DoD séparée pour l'infrastructure, un journal des révisions.

Simple :
```markdown
## Definition of Done
Une User Story est terminée si :
1. Tous ses critères d'acceptation sont vérifiés.
2. Le code est testé.
3. Les droits d'accès sont testés avec chaque profil.
4. Le code est commité et mergé sur le dépôt Git.
5. La User Story est validée par le Product Owner.
```

**Exemple — User Story**

Trop chargé : priorité, valeur métier, points, sprint cible, 8 critères dont des cas limites.

Simple :
```markdown
**US-03 — Créer une pré-admission** · Must
En tant que secrétaire médicale, je veux créer une pré-admission, afin de préparer le dossier avant l'arrivée du patient.
- Champs saisis : identité, coordonnées, motif, service, date d'entrée.
- Les champs obligatoires sont contrôlés.
- La pré-admission est créée au statut « En attente ».
```

## 4. Ne rien inventer en silence

- Si une information manque dans les sources (version, système, outil), mettre une valeur raisonnable dans le document et **le signaler en une ligne dans la réponse**, pas dans le document.
- Si la demande contient une erreur probable ou une faille (ex. TFTP pour déposer les fichiers d'une application web), écrire le bon choix, le dire clairement avec la raison, et proposer de revenir à la demande initiale.
- Ne poser une question que si la réponse change le document.

## 5. Vérifier avant de rendre

- Comparer le document à la liste de l'étape 1 : chaque élément demandé est-il présent ?
- Après avoir simplifié ou supprimé un document, chercher dans les **autres** documents du dossier les références à ce qui a disparu (numéros de critères, sections, liens) et les corriger.
- Signaler ce que Claude ne peut pas faire à la place de l'utilisateur (créer un tableau Trello, obtenir une validation, pousser sur un dépôt distant qui n'existe pas encore).

## 6. Une étape à la fois

Si l'utilisateur avance dans un ordre du jour ou une suite d'étapes, traiter l'étape en cours, puis attendre sa validation avant la suivante. Ne pas produire d'avance les livrables des étapes suivantes.

## 7. La réponse à l'utilisateur

Courte :
- ce qui a été fait ;
- ce qui a été retiré, en une ligne ;
- les choix à vérifier.

## PDF

Si l'utilisateur veut un PDF :

```bash
python <dossier-du-skill>/scripts/md2pdf.py document.md [autre.md ...] [--paysage] [--out dossier]
```

Utiliser `--paysage` pour les tableaux de plus de 6 colonnes. Le script nécessite le module `markdown` (`pip install markdown`) et Chrome ou Edge. Après génération, vérifier que la dernière colonne des grands tableaux apparaît bien dans le PDF.
