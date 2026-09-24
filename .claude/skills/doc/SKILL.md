---
name: doc
description: Crée une documentation ou un document en PDF avec la charte graphique habituelle (bleu marine, tableaux, A4), rédigé automatiquement en mode /simplifie même si l'utilisateur ne le demande pas. Utilise ce skill dès que l'utilisateur tape /doc, ou demande « fais-moi une doc », « une documentation en pdf », « un pdf propre », « un résumé en pdf », « documente ça ».
---

# Doc

Produire une documentation en PDF : contenu simple (règles de `/simplifie`), mise en forme avec la charte habituelle.

## Étapes

1. **Charger `/simplifie`** avec le Skill tool, sans que l'utilisateur le demande, et appliquer ses règles : uniquement ce qui est demandé, phrases courtes, tableaux et listes, pas d'intro ni de conclusion décoratives, pas d'emojis, vocabulaire du sujet.
2. **Lire les sources** du dossier (sujet, PDF, code, échanges de la conversation) et lister ce que la doc doit contenir.
3. **Écrire le Markdown** dans le dossier du projet : `# Titre` unique, puis `##` pour les rubriques, `###` pour les sous-parties. Tableaux Markdown pour les comparaisons. Blocs de code pour le code.
4. **Générer le PDF** avec la charte habituelle (script du skill `simplifie`) :

```bash
python ~/.claude/skills/simplifie/scripts/md2pdf.py document.md [--paysage] [--out dossier]
```

   - `--paysage` si un tableau dépasse 6 colonnes.
   - Le script demande `pip install markdown` et Chrome ou Edge.
5. **Vérifier le PDF** : rubriques demandées présentes, dernière colonne des tableaux visible, pas de page presque vide.
6. **Envoyer le fichier** à l'utilisateur (SendUserFile).

## Charte graphique (fournie par md2pdf.py)

- A4, marges 14 × 12 mm, police Segoe UI / Calibri 9,5 pt.
- Titres et en-têtes de tableau en bleu marine `#0f2b46`, sous-titres `#24486d`.
- Tableaux : en-tête marine, lignes alternées gris clair `#f4f7fa`, bordures `#c8d2dc`.
- Citations et code sur fond gris-bleu clair.

Ne pas utiliser reportlab ni une autre mise en forme : la charte vient uniquement de `md2pdf.py`.

## Réponse à l'utilisateur

Courte : fichier créé, ce qui a été retiré en une ligne, choix à vérifier.
