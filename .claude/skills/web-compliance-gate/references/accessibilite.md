# Accessibilité — exigences et corrections

L'accessibilité fait partie de l'audit parce qu'elle conditionne le score Lighthouse, le SEO, et qu'elle est une obligation légale pour une partie des sites. Référentiels : WCAG 2.1/2.2 niveau AA, RGAA 4.1 (déclinaison française).

## Contrôles automatisés (A11Y-01 à A11Y-06)
- **axe-core** (A11Y-02) sur les 5 premières pages : zéro violation *critical* ou *serious*. Chaque violation donne la règle (`image-alt`, `label`, `color-contrast`, `button-name`, `link-name`, `html-has-lang`, `aria-*`…) et un sélecteur d'exemple : corriger à la source (composant), pas page par page.
- **Lighthouse Accessibilité** ≥ 90 (A11Y-01).
- Automatisé ≠ complet : axe détecte environ un tiers à la moitié des problèmes WCAG. Vérifier aussi à la main : navigation au clavier (Tab/Maj+Tab/Entrée/Échap), focus visible, ordre logique, lecteur d'écran sur le parcours principal (NVDA ou VoiceOver).

<a id="formulaires"></a>
## Formulaires (A11Y-03)
```html
<label for="email">Adresse email <span aria-hidden="true">*</span></label>
<input id="email" name="email" type="email" autocomplete="email" required aria-describedby="email-aide">
<p id="email-aide">Nous l'utilisons uniquement pour vous répondre.</p>
```
- Un `<label for>` par champ (le `placeholder` ne remplace pas le label).
- Attributs `autocomplete` adaptés (name, email, tel, street-address, postal-code, current-password…).
- Erreurs : message textuel lié au champ (`aria-describedby`), `aria-invalid="true"`, focus déplacé vers le premier champ en erreur.

## Essentiels
- Boutons et liens avec un nom accessible (A11Y-04) : texte visible, ou `aria-label` pour les boutons icônes (`<button aria-label="Ouvrir le menu">`).
- Zoom autorisé (A11Y-05) : jamais `user-scalable=no` ni `maximum-scale=1`.
- Structure (A11Y-06) : `<header> <nav> <main> <footer>`, lien d'évitement « Aller au contenu » en premier élément focusable.
- Contrastes : 4,5:1 pour le texte normal, 3:1 pour le grand texte et les composants d'interface.
- Images : `alt` pertinent ; `alt=""` si décorative.
- Langue : `<html lang="fr">` ; `lang="en"` sur les passages dans une autre langue.
- Animations : respecter `prefers-reduced-motion`.
- Bandeau cookies et modales : focus piégé dans la modale, fermeture avec Échap, retour du focus à l'élément déclencheur.

<a id="obligations"></a>
## Obligations légales (A11Y-07) — à vérifier avec le client
- **Secteur public** et entreprises au chiffre d'affaires > 250 M€ en France : conformité RGAA, **déclaration d'accessibilité** publiée, mention « Accessibilité : non / partiellement / totalement conforme » en pied de page, schéma pluriannuel.
- **Acte européen sur l'accessibilité (EAA)**, applicable depuis le 28 juin 2025 : concerne notamment le commerce électronique, les services bancaires, le transport et les communications électroniques. Les **microentreprises de services** (moins de 10 salariés et CA ou bilan ≤ 2 M€) en sont exemptées. Un site e-commerce d'une PME au-delà de ces seuils est concerné : conformité WCAG AA de fait + déclaration d'accessibilité.
- Le périmètre exact dépend du client (secteur, taille, activité) : poser la question et consigner la réponse dans `answers.json`.
