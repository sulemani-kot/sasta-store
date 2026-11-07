#!/usr/bin/env python3
"""Har product ka alag page + sitemap banata hai (GitHub robot isay chalata hai).
Chalana: python3 gen_products.py  (repo ke root mein)"""
import json, os, re, sys, html, glob, unicodedata, urllib.parse, datetime

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
MARK = "<!--sasta-product-page-->"
SKIP = {"index.html", "admin.html", "404.html"}

def rd(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()

def wr(p, s):
    old = None
    fp = os.path.join(ROOT, p)
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            old = f.read()
    if old == s:
        return False
    with open(fp, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    return True

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
clean = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()

def jld(o):
    return json.dumps(o, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

def slugify(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 50:
        cut = s[:50]
        if s[50] != "-" and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        s = cut.strip("-")
    return s or "product"

def short(t, n):
    t = clean(t)
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(",.;:-") + "…"

def fin(p):
    try:
        return int(round(float(p.get("price") or 0) * (1 - float(p.get("discount") or 0) / 100)))
    except Exception:
        return 0

def put_tag(h, pat, new):
    """pehle se tag ho to badlo, warna </head> se pehle daalo"""
    if re.search(pat, h):
        return re.sub(pat, lambda m: new, h, count=1)
    return h.replace("</head>", new + "</head>", 1)

def drop_tag(h, pat):
    return re.sub(pat, "", h)

def main():
    T = rd("index.html")
    data = json.loads(rd("data.json"))
    prods = [p for p in data.get("products", []) if isinstance(p, dict) and p.get("id") and p.get("name")]
    st = data.get("settings", {}) or {}

    m = re.search(r'<link rel="canonical" href="([^"]+)"', T)
    site = (m.group(1) if m else "").rstrip("/") + "/"
    if not site.startswith("http"):
        print("ERROR: index.html mein canonical link nahi mila"); sys.exit(1)
    m = re.search(r'<meta property="og:site_name" content="([^"]*)"', T)
    brand = html.unescape(m.group(1)) if m else "SASTA STORE"
    brand_short = brand.split(" - ")[0]
    img_abs = lambda u: u if re.match(r"^https?:", u or "") else (site + urllib.parse.quote(u.lstrip("/"), safe="/") if u and not u.startswith("data:") else "")

    used, files, pages = set(), {}, []
    for p in prods:
        pid = re.sub(r"[^A-Za-z0-9_-]", "", str(p["id"])) or "x"
        fn = f"{slugify(p['name'])}-{pid}.html"
        if fn in used or fn in SKIP:
            fn = f"product-{pid}.html"
        used.add(fn)
        url = site + fn
        price, name = fin(p), clean(p["name"])
        instock = (p.get("stock") or 0) > 0 if isinstance(p.get("stock"), (int, float)) else str(p.get("stock") or "0").isdigit() and int(p["stock"]) > 0
        imgs = [img_abs(i) for i in (p.get("images") or []) if isinstance(i, str)]
        imgs = [i for i in imgs if i][:6]
        cond = {"new": "NewCondition", "used": "UsedCondition", "refurbished": "RefurbishedCondition"}.get(str(p.get("condition") or "").strip().lower().split()[0] if p.get("condition") else "", "")
        title = f"{name} - Rs. {price:,} | {brand_short}"
        if len(title) > 72:
            title = f"{name} | {brand_short}"
        tail = f" Rs. {price:,}. WhatsApp par order karein - {brand_short}."
        desc = (short(p.get("description"), max(40, 158 - len(tail))) + tail) if clean(p.get("description")) else f"{name}.{tail}"
        desc = desc.strip()

        h = T
        h = re.sub(r"(?s)<title>.*?</title>", lambda m: f"<title>{esc(title)}</title>", h, count=1)
        h = put_tag(h, r'<meta name="description"[^>]*>', f'<meta name="description" content="{esc(desc)}">')
        h = put_tag(h, r'<link rel="canonical"[^>]*>', f'<link rel="canonical" href="{esc(url)}">')
        h = put_tag(h, r'<meta property="og:type"[^>]*>', '<meta property="og:type" content="product">')
        h = put_tag(h, r'<meta property="og:title"[^>]*>', f'<meta property="og:title" content="{esc(title)}">')
        h = put_tag(h, r'<meta property="og:description"[^>]*>', f'<meta property="og:description" content="{esc(desc)}">')
        h = put_tag(h, r'<meta property="og:url"[^>]*>', f'<meta property="og:url" content="{esc(url)}">')
        h = drop_tag(h, r'<meta property="og:image:(width|height)"[^>]*>')
        if imgs:
            h = put_tag(h, r'<meta property="og:image"[^>]*>', f'<meta property="og:image" content="{esc(imgs[0])}">')
            h = put_tag(h, r'<meta name="twitter:image"[^>]*>', f'<meta name="twitter:image" content="{esc(imgs[0])}">')
            h = put_tag(h, r'<meta name="twitter:card"[^>]*>', '<meta name="twitter:card" content="summary_large_image">')
        h = put_tag(h, r'<meta name="twitter:title"[^>]*>', f'<meta name="twitter:title" content="{esc(title)}">')
        h = put_tag(h, r'<meta name="twitter:description"[^>]*>', f'<meta name="twitter:description" content="{esc(desc)}">')

        offer = {"@type": "Offer", "url": url, "priceCurrency": "PKR", "price": str(price),
                 "availability": "https://schema.org/" + ("InStock" if instock else "OutOfStock"),
                 "seller": {"@type": "Organization", "name": brand_short}}
        if cond:
            offer["itemCondition"] = "https://schema.org/" + cond
        prod = {"@context": "https://schema.org", "@type": "Product", "name": name, "sku": str(p["id"]),
                "description": (re.sub(r"\n{3,}", "\n\n", str(p.get("description") or "").strip())[:4000] or name),
                "offers": offer}
        if imgs:
            prod["image"] = imgs
        if p.get("category"):
            prod["category"] = clean(p["category"])
        extra = (MARK + f'<script type="application/ld+json">{jld(prod)}</script>'
                 f'<meta property="product:price:amount" content="{price}"><meta property="product:price:currency" content="PKR">'
                 f'<script>window.__PID={json.dumps(str(p["id"]))}</script>')
        h = h.replace("</head>", extra + "</head>", 1)

        # JS band ho to bhi product ki tafseel (home wali noscript ki jagah)
        phone = clean(st.get("phone"))
        ns = ('<noscript><div style="font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:28px 18px;color:#1d312a;line-height:1.7">'
              f'<h1>{esc(name)}</h1>' + (f'<p><img src="{esc(imgs[0])}" alt="{esc(name)}" style="max-width:100%;height:auto"></p>' if imgs else "") +
              f'<p><b>Rs. {price:,}</b> - {"In stock" if instock else "Out of stock"}</p>'
              + (f'<p>{esc(p.get("category"))}{", " + esc(p.get("condition")) + " condition" if p.get("condition") else ""}</p>' if p.get("category") else "")
              + f'<p style="white-space:pre-line">{esc(str(p.get("description") or "").strip())}</p>'
              f'<p><a href="./">{esc(brand)} - sab products</a></p>'
              + (f'<p>WhatsApp / Phone: {esc(phone)}</p>' if phone else "") + '</div></noscript>')
        i = h.find("<body>")
        mm = re.search(r"<noscript>(?!<style).*?</noscript>", h[i:], re.S) if i >= 0 else None
        if mm:
            h = h[:i + mm.start()] + ns + h[i + mm.end():]
        elif i >= 0:
            h = h[:i + 6] + ns + h[i + 6:]
        files[fn] = h
        pages.append((fn, url))

    ch = {"new": 0, "upd": 0, "del": 0}
    for fn, s in files.items():
        existed = os.path.exists(os.path.join(ROOT, fn))
        if wr(fn, s):
            ch["upd" if existed else "new"] += 1
    for fp in glob.glob(os.path.join(ROOT, "*.html")):
        fn = os.path.basename(fp)
        if fn in files or fn in SKIP:
            continue
        with open(fp, encoding="utf-8", errors="ignore") as f:
            if MARK in f.read():
                os.remove(fp); ch["del"] += 1

    # sitemap
    home_lm = datetime.date.today().isoformat()
    try:
        mlm = re.search(r"<lastmod>([^<]+)</lastmod>", rd("sitemap.xml"))
        if mlm:
            home_lm = mlm.group(1)
    except Exception:
        pass
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          f"  <url>\n    <loc>{esc(site)}</loc>\n    <lastmod>{home_lm}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for fn, url in sorted(pages):
        sm.append(f"  <url>\n    <loc>{esc(url)}</loc>\n    <priority>0.8</priority>\n  </url>")
    sm.append("</urlset>\n")
    sm_changed = wr("sitemap.xml", "\n".join(sm))
    print(f"Products: {len(pages)} | naye pages: {ch['new']} | badle: {ch['upd']} | hataye: {ch['del']} | sitemap badli: {sm_changed}")

main()
