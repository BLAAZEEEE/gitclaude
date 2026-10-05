"""Domaines et cookies de traceurs connus (soumis à consentement sauf mention)."""
import re

# domaine (suffixe) -> (service, catégorie)
TRACKER_DOMAINS = {
    "google-analytics.com": ("Google Analytics", "mesure"), "analytics.google.com": ("Google Analytics", "mesure"),
    "googletagmanager.com": ("Google Tag Manager", "mesure"), "doubleclick.net": ("Google Ads / DoubleClick", "pub"),
    "googlesyndication.com": ("Google AdSense", "pub"), "googleadservices.com": ("Google Ads", "pub"),
    "google.com/ads": ("Google Ads", "pub"), "google.com/pagead": ("Google Ads", "pub"),
    "connect.facebook.net": ("Meta Pixel", "pub"), "facebook.com/tr": ("Meta Pixel", "pub"),
    "hotjar.com": ("Hotjar", "mesure"), "hotjar.io": ("Hotjar", "mesure"), "clarity.ms": ("Microsoft Clarity", "mesure"),
    "bat.bing.com": ("Microsoft Ads", "pub"), "snap.licdn.com": ("LinkedIn Insight", "pub"), "px.ads.linkedin.com": ("LinkedIn Ads", "pub"),
    "analytics.tiktok.com": ("TikTok Pixel", "pub"), "static.ads-twitter.com": ("X/Twitter Ads", "pub"), "analytics.twitter.com": ("X/Twitter", "pub"),
    "ct.pinterest.com": ("Pinterest Tag", "pub"), "sc-static.net": ("Snap Pixel", "pub"), "criteo.com": ("Criteo", "pub"), "criteo.net": ("Criteo", "pub"),
    "taboola.com": ("Taboola", "pub"), "outbrain.com": ("Outbrain", "pub"), "mixpanel.com": ("Mixpanel", "mesure"),
    "cdn.segment.com": ("Segment", "mesure"), "api.segment.io": ("Segment", "mesure"), "amplitude.com": ("Amplitude", "mesure"),
    "heapanalytics.com": ("Heap", "mesure"), "fullstory.com": ("FullStory", "mesure"), "mouseflow.com": ("Mouseflow", "mesure"),
    "crazyegg.com": ("Crazy Egg", "mesure"), "js.hs-scripts.com": ("HubSpot", "marketing"), "js.hs-analytics.net": ("HubSpot", "marketing"),
    "track.hubspot.com": ("HubSpot", "marketing"), "js.hsforms.net": ("HubSpot Forms", "marketing"), "widget.intercom.io": ("Intercom", "chat"),
    "client.crisp.chat": ("Crisp", "chat"), "static.zdassets.com": ("Zendesk", "chat"), "embed.tawk.to": ("Tawk.to", "chat"),
    "addthis.com": ("AddThis", "social"), "sharethis.com": ("ShareThis", "social"), "disqus.com": ("Disqus", "social"),
    "platform.twitter.com": ("Widget X/Twitter", "social"), "platform.linkedin.com": ("Widget LinkedIn", "social"),
    "instagram.com/embed": ("Embed Instagram", "social"), "tiktok.com/embed": ("Embed TikTok", "social"),
    "yandex.ru": ("Yandex Metrica", "mesure"), "mc.yandex.ru": ("Yandex Metrica", "mesure"), "quantserve.com": ("Quantcast", "pub"),
    "adnxs.com": ("Xandr", "pub"), "rubiconproject.com": ("Magnite", "pub"), "pubmatic.com": ("PubMatic", "pub"),
    "smartadserver.com": ("Smart AdServer", "pub"), "matomo.cloud": ("Matomo Cloud", "mesure-exemptable"),
    "cdn.matomo.cloud": ("Matomo Cloud", "mesure-exemptable"),
}
EMBED_DOMAINS = {
    "youtube.com": "YouTube", "youtube-nocookie.com": "YouTube (nocookie)", "ytimg.com": "YouTube", "player.vimeo.com": "Vimeo",
    "vimeocdn.com": "Vimeo", "maps.googleapis.com": "Google Maps", "maps.google.com": "Google Maps", "google.com/maps": "Google Maps",
    "dailymotion.com": "Dailymotion", "open.spotify.com": "Spotify", "w.soundcloud.com": "SoundCloud", "calendly.com": "Calendly",
    "facebook.com/plugins": "Widget Facebook",
}
FONT_DOMAINS = {"fonts.googleapis.com": "Google Fonts", "fonts.gstatic.com": "Google Fonts", "use.typekit.net": "Adobe Fonts",
                "fonts.bunny.net": "Bunny Fonts (UE)", "use.fontawesome.com": "Font Awesome CDN", "kit.fontawesome.com": "Font Awesome Kit"}
CAPTCHA_DOMAINS = {"google.com/recaptcha": "reCAPTCHA", "gstatic.com/recaptcha": "reCAPTCHA", "recaptcha.net": "reCAPTCHA",
                   "hcaptcha.com": "hCaptcha", "challenges.cloudflare.com": "Cloudflare Turnstile", "friendlycaptcha": "Friendly Captcha"}
CDN_DOMAINS = {"cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com", "code.jquery.com", "stackpath.bootstrapcdn.com",
               "maxcdn.bootstrapcdn.com", "ajax.googleapis.com", "cdn.tailwindcss.com", "esm.sh", "cdn.skypack.dev"}

TRACKER_COOKIES = re.compile(
    r"^(_ga($|_)|_gid$|_gat|_gcl_|_fbp$|_fbc$|fr$|_hj|_clck$|_clsk$|MUID$|_uet|IDE$|test_cookie$|NID$|__gads|__gpi|"
    r"li_sugr$|bcookie$|lidc$|UserMatchHistory$|AnalyticsSyncHistory$|_pin_unauth$|_pinterest|_tt_enable_cookie$|_ttp$|"
    r"__hstc$|hubspotutk$|__hssc$|__hssrc$|_pk_id|_pk_ses|mp_|ajs_|amp_|AMP_|_hp2_|_mkto_trk$|intercom-|crisp-client|"
    r"__utm|_scid|_sctr|_rdt_uuid|_tt_|tt_|cto_bundle$|_cc_|__qca$|_derived_epik$|_dc_gtm)", re.I)
# cookies généralement « strictement nécessaires » ou de choix de consentement
CONSENT_COOKIES = re.compile(r"(consent|cookieconsent|cc_cookie|tarteaucitron|axeptio|didomi|euconsent|cookielawinfo|cmplz|klaro|OptanonConsent|CookieConsent|borlabs|complianz|cookie_notice|cookies_policy|gdpr)", re.I)
LS_TRACKER_KEYS = re.compile(r"^(_ga|amplitude|AMP_|mp_|ajs_|_hj|_clck|_cltk|_uetsid|_uetvid|__anon_id|segment|mixpanel|heap|fs_uid|_fbp|_ttp|tt_)", re.I)


def classify(url: str):
    u = url.split("://", 1)[-1]
    for d, (name, cat) in TRACKER_DOMAINS.items():
        if _match(u, d):
            return ("tracker", name, cat)
    for d, name in CAPTCHA_DOMAINS.items():
        if _match(u, d):
            return ("captcha", name, "captcha")
    for d, name in EMBED_DOMAINS.items():
        if _match(u, d):
            return ("embed", name, "embed")
    for d, name in FONT_DOMAINS.items():
        if _match(u, d):
            return ("font", name, "font")
    host = u.split("/", 1)[0].split(":")[0]
    if host in CDN_DOMAINS:
        return ("cdn", host, "cdn")
    return None


def _match(u: str, d: str) -> bool:
    host, _, path = u.partition("/")
    host = host.split(":")[0]
    if "/" in d:
        dh, dp = d.split("/", 1)
        return (host == dh or host.endswith("." + dh)) and path.startswith(dp)
    return host == d or host.endswith("." + d)
