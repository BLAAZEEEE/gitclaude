# RGPD, cookies & mentions obligatoires — exigences et corrections

Sommaire : [consentement](#consentement) · [bandeau](#bandeau) · [durées](#durees) · [services tiers](#tiers) · [mentions légales](#mentions-legales) · [modèle mentions](#modele-mentions) · [politique de confidentialité](#politique) · [modèle politique](#modele-politique) · [CGV/CGU](#cgv) · [formulaires](#formulaires) · [contrôles documentaires](#documentaire)

Textes : RGPD (UE 2016/679) · loi Informatique et Libertés art. 82 (traceurs) · lignes directrices + recommandation « cookies et autres traceurs » de la CNIL · LCEN art. 6 III et 19 (mentions légales) · Code de la consommation (CGV, médiateur) · CPCE L34-5 (prospection par email).

Ce que l'audit couvre : la conformité **technique observable** (ce que le site fait réellement dans un navigateur, ce qu'il affiche, ce que le code contient) + les **contrôles documentaires** posés sous forme de questions. La justesse juridique du contenu des documents (finalités réelles, durées choisies) reste de la responsabilité du client : Claude signale, le client valide.

---

<a id="consentement"></a>
## 1. Consentement aux traceurs (RGPD-01/02/03/07/08/17)

Règle : **aucun traceur soumis à consentement ne doit être lu ou écrit avant un clic « Accepter »**. Cela vaut pour les cookies, localStorage/sessionStorage, pixels, fingerprinting, et pour tout appel à un domaine tiers qui dépose des identifiants.

Soumis à consentement (liste non exhaustive) : Google Analytics / GA4, Google Tag Manager qui charge des balises, Google Ads, Meta Pixel, TikTok, LinkedIn Insight, Hotjar, Microsoft Clarity, Mixpanel, Segment, HubSpot tracking, widgets de partage sociaux, vidéos YouTube/Vimeo embarquées, Google Maps embarqué, chat tiers qui trace (Crisp, Intercom, Tawk).

Exemptés (pas de consentement) : cookie de session, panier, jeton CSRF, équilibrage de charge, cookie mémorisant le choix de consentement, authentification, **mesure d'audience exemptée** si toutes les conditions CNIL sont réunies : finalité strictement limitée à la mesure pour le compte exclusif de l'éditeur, données anonymisées/agrégées, pas de recoupement avec d'autres traitements ni de suivi inter-sites, pas de transmission à des tiers, cookies ≤ 13 mois, données conservées ≤ 25 mois, possibilité d'opposition. Matomo auto-hébergé configuré selon le guide CNIL, Plausible et Umami (sans cookie) entrent généralement dans ce cadre. **GA4 n'est pas exempté.**

### Implémentations correctes

**Option A — CMP reconnue** (la plus simple à maintenir) : tarteaucitron.js (open source, FR), orestbida/cookieconsent v3 (open source), Axeptio, Didomi, Cookiebot, Klaro. Les scripts tiers sont déclarés *désactivés* et la CMP les injecte après consentement :

```html
<!-- orestbida/cookieconsent v3 : le script ne s'exécute qu'après consentement « analytics » -->
<script type="text/plain" data-category="analytics" data-service="Google Analytics"
        src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>
```

**Option B — Google Consent Mode v2** (si GTM/gtag obligatoire) — le mode « denied » par défaut **doit** précéder la balise, et les balises non Google restent conditionnées dans GTM :

```html
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied', analytics_storage:'denied', wait_for_update: 500});
</script>
<!-- puis GTM ; la CMP appelle gtag('consent','update',{analytics_storage:'granted'}) au clic « Accepter » -->
```
Attention : en Consent Mode « avancé », gtag envoie quand même des pings sans cookie avant consentement. Pour un audit 100 % propre (RGPD-02), utiliser le mode **basique** : ne charger gtag qu'après consentement.

**Option C — bandeau maison** : acceptable s'il respecte toutes les règles du §2. Squelette minimal :
```js
const CHOICE = 'consent'; const SIX_MONTHS = 15552000;
const get = () => document.cookie.match(new RegExp('(?:^|; )' + CHOICE + '=([^;]+)'))?.[1];
const set = v => document.cookie = `${CHOICE}=${v}; max-age=${SIX_MONTHS}; path=/; SameSite=Lax; Secure`;
function loadTrackers(){ /* injecter ici les <script> tiers */ }
// au chargement : if (get()==='yes') loadTrackers(); else if (!get()) showBanner();
// bouton Accepter : set('yes'); loadTrackers();  bouton Refuser : set('no');
// lien « Gestion des cookies » dans le footer : showBanner()
```
Au retrait du consentement : supprimer les cookies internes posés (`document.cookie = '_ga=; max-age=0; path=/; domain=.site.fr'`) et cesser tout appel aux domaines tiers.

<a id="bandeau"></a>
## 2. Bandeau (RGPD-04/05/06/11/12)

- **Refuser au premier niveau** : bouton « Tout refuser » ou « Continuer sans accepter » visible d'emblée (sanctions CNIL 2021-2022 contre Google, Facebook, Amazon… pour refus plus difficile que l'acceptation).
- **Symétrie** : même composant, même taille, même contraste, même nombre de clics. Pas de refus en lien gris minuscule, pas de « Paramétrer » comme seule alternative.
- **Silence = refus** : poursuivre la navigation, scroller ou fermer la croix ≠ consentement.
- **Information** : finalités, liste des responsables/partenaires accessible (lien vers la politique cookies).
- **Retrait aussi simple que l'acceptation**, accessible à tout moment : lien « Gestion des cookies » dans le footer de chaque page ou bouton flottant.
- **Pas de cookie wall** sauf alternative réelle et équitable (évaluation au cas par cas par la CNIL) : le bandeau ne bloque ni le contenu ni le défilement.
- Accessibilité : `role="dialog"`, `aria-label`, focus clavier sur le bandeau, boutons atteignables au clavier.

<a id="durees"></a>
## 3. Durées (RGPD-09/10)

| Élément | Durée |
|---|---|
| Cookies traceurs (analytics, pub) | 13 mois maximum, non prorogés automatiquement à chaque visite |
| Données de mesure d'audience exemptée | 25 mois maximum |
| Mémorisation du choix (acceptation OU refus) | 6 mois = bonne pratique CNIL ; redemander ensuite |
| Preuve du consentement | conserver le journal (date, version du bandeau, choix) |

GA4 : régler `cookie_expires` à 34 186 669 s (≈ 13 mois) et la conservation des données à 14 mois maximum dans l'admin.

<a id="tiers"></a>
## 4. Services tiers (RGPD-13/14/15/16)

- **Google Fonts distant** : transmet l'IP à Google sans base légale (LG München, 20/01/2022). → auto-héberger : `npm i @fontsource/inter` ou google-webfonts-helper, `@font-face` local, `font-display: swap`. Même logique pour Adobe Fonts et les kits Font Awesome.
- **YouTube / Vimeo / Maps / réseaux sociaux** : façade « cliquer pour charger » (lite-youtube-embed, vignette statique + clic) ou conditionnement à la CMP. `youtube-nocookie.com` réduit mais n'élimine pas les identifiants.
- **reCAPTCHA** : Google collecte des données comportementales → préférer honeypot + limitation de débit, Friendly Captcha (UE), ou Cloudflare Turnstile/hCaptcha mentionnés dans la politique ; ne charger le captcha que sur la page du formulaire.
- **CDN publics** (jsDelivr, cdnjs, unpkg, code.jquery.com) : transfert d'IP → auto-héberger via le bundler ; sinon les citer comme destinataires et ajouter SRI (voir securite.md).
- **Transferts hors UE** : services US certifiés **EU-US Data Privacy Framework** (depuis juillet 2023) = transfert encadré, à mentionner. Sinon clauses contractuelles types + analyse. Préférer des prestataires UE quand c'est possible.

<a id="mentions-legales"></a>
## 5. Mentions légales (RGPD-20/21) — LCEN art. 6 III

Page dédiée, liée depuis le pied de **toutes** les pages. Contenu obligatoire :

**Éditeur professionnel (entreprise, micro-entrepreneur, association)**
- Dénomination ou raison sociale / nom et prénom de l'entrepreneur individuel (+ mention « EI » ou « Entrepreneur individuel »)
- Adresse du siège (ou domiciliation), numéro de téléphone, adresse email
- Forme juridique et capital social (sociétés)
- N° d'immatriculation : SIREN/SIRET, RCS + ville, ou Répertoire des métiers
- N° de TVA intracommunautaire (si assujetti ; micro-entreprise en franchise : « TVA non applicable, art. 293 B du CGI » sur les factures)
- Directeur ou responsable de la publication (personne physique)
- Activité réglementée : ordre professionnel, titre, règles applicables

**Hébergeur** : nom/raison sociale, adresse, **numéro de téléphone** (souvent oublié).

**Particulier non professionnel** : peut rester anonyme vis-à-vis du public mais doit communiquer son identité à l'hébergeur ; les coordonnées de l'hébergeur restent obligatoires.

<a id="modele-mentions"></a>
### Modèle (à compléter, ne jamais publier de valeurs inventées)
```markdown
# Mentions légales
## Éditeur du site
[Raison sociale / Nom Prénom EI], [forme juridique] au capital de [X] € (si société)
Siège : [adresse complète]
SIREN/SIRET : [n°] — [RCS Ville n° / RM n°]
TVA intracommunautaire : [FRxx...] (si applicable)
Téléphone : [n°] — Email : [adresse]
## Directeur de la publication
[Nom Prénom], [qualité]
## Hébergement
[Nom de l'hébergeur], [adresse], [téléphone]
## Propriété intellectuelle
[Contenus, crédits photos, licences]
## Données personnelles
Voir notre [politique de confidentialité](/politique-de-confidentialite).
```
Hébergeurs courants : IONOS SARL, 7 place de la Gare, 57200 Sarreguemines · OVH SAS, 2 rue Kellermann, 59100 Roubaix · o2switch, Chemin des Pardiaux, 63000 Clermont-Ferrand. **Toujours vérifier l'adresse et le téléphone à jour sur le site de l'hébergeur avant publication.**

<a id="politique"></a>
## 6. Politique de confidentialité (RGPD-22/23/24) — art. 13 RGPD

Doit contenir, rédigé clairement :
1. Identité et coordonnées du **responsable du traitement** (+ DPO s'il existe)
2. **Finalités** de chaque traitement (contact, devis, compte client, newsletter, mesure d'audience…)
3. **Base légale** de chacune : consentement, contrat/mesures précontractuelles, obligation légale, intérêt légitime (le préciser)
4. **Destinataires** et catégories de sous-traitants (hébergeur, emailing, paiement, analytics)
5. **Transferts hors UE** et garanties (DPF, CCT)
6. **Durées de conservation** par finalité (ou critères)
7. Les **droits** : accès, rectification, effacement, limitation, portabilité, opposition ; retrait du consentement à tout moment ; directives post-mortem (loi FR)
8. Droit d'introduire une **réclamation auprès de la CNIL**
9. Caractère obligatoire ou facultatif des données et conséquences d'un défaut de réponse
10. Existence d'une décision automatisée / profilage le cas échéant
11. **Section cookies** : liste des traceurs (nom, émetteur, finalité, durée), lien de gestion des cookies

<a id="modele-politique"></a>
### Durées de référence (référentiels CNIL, à adapter)
| Traitement | Durée active | Ensuite |
|---|---|---|
| Demandes de contact / prospects | 3 ans après le dernier contact | suppression |
| Clients (relation commerciale) | durée de la relation | archivage intermédiaire (ex. 5 ans preuve, 10 ans pièces comptables) |
| Compte utilisateur inactif | 2 à 3 ans d'inactivité avec relance | suppression |
| Candidatures non retenues | 2 ans (avec accord) | suppression |
| Journaux de connexion (sécurité) | 6 mois à 1 an | suppression |
| Newsletter | jusqu'au désabonnement | liste d'opposition |

<a id="cgv"></a>
## 7. CGV / CGU / médiateur (RGPD-25/26)

- **Vente en ligne B2C** : CGV obligatoires et acceptées avant commande (case non pré-cochée), prix TTC, frais de livraison, droit de rétractation de 14 jours + formulaire type, garanties légales (conformité, vices cachés), modalités de paiement, **médiateur de la consommation** (nom + site web, art. L612-1 et L616-1 C. conso), lien vers la plateforme européenne RLL si applicable (vérifier son statut actuel).
- **Espace membre / plateforme** : CGU recommandées (règles d'usage, responsabilité, résiliation).
- **Prestations de service B2B** : CGV communicables sur demande (art. L441-1 C. com.).

<a id="formulaires"></a>
## 8. Formulaires (RGPD-30/31/32/33/34)

- **Mention d'information** sous chaque formulaire (1er niveau) :
  > Les informations recueillies sont traitées par [responsable] pour [finalité], sur la base de [base légale]. Elles sont conservées [durée] et destinées à [destinataires]. Vous pouvez exercer vos droits d'accès, de rectification, d'effacement… en écrivant à [contact]. En savoir plus : [politique de confidentialité].
- **Aucune case pré-cochée** (newsletter, partenaires, acceptation des CGU).
- **Newsletter B2C = opt-in** explicite (CPCE L34-5) ; lien de désinscription dans chaque email.
- **Minimisation** : ne demander que le nécessaire. Date de naissance, civilité, téléphone, adresse → uniquement si justifiés par la finalité. Champs facultatifs marqués comme tels.
- **Données sensibles (art. 9)** : santé, opinions, religion, orientation, biométrie… → base légale spécifique (consentement explicite le plus souvent), AIPD, sécurité renforcée. **Données de santé en France** : hébergeur certifié **HDS** obligatoire quand on héberge des données de santé pour le compte de patients ou de professionnels de santé (art. L1111-8 Code de la santé publique).
- Transmission en **HTTPS** uniquement ; pas de données personnelles dans l'URL (GET).

<a id="documentaire"></a>
## 9. Contrôles documentaires (RGPD-D01 à D09) — invisibles dans le code

Questions à poser au client (fichier `answers.json` généré par `audit.py --questions`) :

| ID | Question | Si « non » : que faire |
|---|---|---|
| D01 | Registre des activités de traitement tenu (art. 30) ? | Modèle CNIL (tableur) : une fiche par traitement |
| D02 | Contrats de sous-traitance art. 28 avec chaque prestataire ? | Accepter/télécharger les DPA (IONOS, OVH, Brevo, Google…) |
| D03 | Données hébergées dans l'UE ou transferts encadrés ? | Vérifier chaque prestataire, documenter DPF/CCT |
| D04 | Durées de conservation appliquées (purge) ? | Cron/tâche planifiée de suppression, TTL en base |
| D05 | Procédure d'exercice des droits (réponse ≤ 1 mois) ? | Adresse dédiée + procédure écrite + modèle de réponse |
| D06 | Procédure de violation de données (CNIL sous 72 h, art. 33) ? | Procédure + registre des violations |
| D07 | AIPD si traitement à risque (santé, profilage, grande échelle, surveillance) ? | Outil PIA de la CNIL |
| D08 | Preuve des consentements conservée ? | Journalisation CMP / horodatage des opt-in |
| D09 | DPO désigné si obligatoire ? | Obligatoire : organismes publics, suivi régulier à grande échelle, données sensibles à grande échelle |

Les mesures de sécurité (art. 32) sont dans securite.md.
