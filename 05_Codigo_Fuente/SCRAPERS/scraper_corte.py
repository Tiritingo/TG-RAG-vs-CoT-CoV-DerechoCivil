import re
import json
import time
import random
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE_URL = "https://www.corteconstitucional.gov.co"
SEARCH_URL = f"{BASE_URL}/relatoria/buscador-jurisprudencia"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

BASE_DIR = Path.cwd() / "Corte Constitucional"
DOC_DIR = BASE_DIR / "documentos"
META_DIR = BASE_DIR / "meta"

DOC_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS = False


def log(msg):
    print(msg, flush=True)


def clean_filename(text):
    if text is None:
        text = "sin_nombre"
    text = re.sub(r'[\\/*?:"<>|]+', "_", str(text))
    text = re.sub(r"\s+", "_", text.strip())
    return text[:180]


def absolutize(url):
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(BASE_URL, url)


def file_ext_from_url(url):
    if not url:
        return None
    path = urlparse(url).path.lower()
    for ext in [".pdf", ".rtf", ".htm", ".html", ".doc", ".docx"]:
        if path.endswith(ext):
            return ext
    return None


def polite_sleep(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))


def save_binary(url, path, timeout=120):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


def save_text(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def launch_browser(headless=HEADLESS):
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=headless,
        args=["--disable-dev-shm-usage"],
    )
    return p, browser


def dump_debug_page(page, prefix):
    html_path = META_DIR / f"{prefix}.html"
    png_path = META_DIR / f"{prefix}.png"

    try:
        save_text(page.content(), html_path)
    except Exception:
        pass

    try:
        page.screenshot(path=str(png_path), full_page=True)
    except Exception:
        pass

    return {
        "html_path": str(html_path),
        "png_path": str(png_path),
    }


def smoke_test_search():
    p, browser = launch_browser()
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 1800})
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(90000)

        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        title = page.title()
        content = page.content()
        debug = dump_debug_page(page, "smoke_test_search")

        blocked = "blocked" in title.lower() or "blocked" in content.lower()

        out = {
            "title": title,
            "blocked": blocked,
            "search_url": SEARCH_URL,
            **debug,
        }

        save_json(out, META_DIR / "smoke_test_search.json")
        log(json.dumps(out, ensure_ascii=False, indent=2))
        return out

    finally:
        browser.close()
        p.stop()


def is_auto_record(text):
    if not text:
        return False

    text = str(text).strip().upper()

    patterns = [
        r"^A\d{1,4}[-/]\d{2,4}$",
        r"\bA\d{1,4}[-/]\d{2,4}\b",
        r"^AUTO\b",
        r"\bAUTO\b",
    ]

    return any(re.search(p, text) for p in patterns)


def find_search_input(page):
    candidate_selectors = [
        'input#textoBuscador',
        'input[name="textoBuscador"]',
        'input[placeholder*="palabra" i]',
        'input[placeholder*="frase" i]',
        'input[title*="palabra" i]',
        'input[aria-label*="Palabras" i]',
        'input[aria-label*="frases" i]',
        'input[type="search"]',
        'input.form-control',
    ]

    for selector in candidate_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                first = locator.first
                first.wait_for(state="visible", timeout=5000)
                return first, selector
        except Exception:
            pass

    try:
        generic_inputs = page.locator("input")
        n = generic_inputs.count()

        for i in range(n):
            item = generic_inputs.nth(i)
            try:
                input_type = item.get_attribute("type")
                placeholder = item.get_attribute("placeholder") or ""
                name = item.get_attribute("name") or ""
                _id = item.get_attribute("id") or ""
                title = item.get_attribute("title") or ""
                aria = item.get_attribute("aria-label") or ""

                blob = f"{placeholder} {name} {_id} {title} {aria}".lower()
                if input_type in [None, "text", "search"] and any(k in blob for k in ["busca", "palabra", "frase", "texto"]):
                    item.wait_for(state="visible", timeout=3000)
                    return item, f"generic_match::{_id or name or placeholder or aria}"
            except Exception:
                pass
    except Exception:
        pass

    raise RuntimeError("No se encontró el input de búsqueda con ninguno de los selectores probados.")


def find_search_button(page):
    try:
        btn = page.get_by_role("button", name="Buscar")
        if btn.count() > 0:
            return btn.first, "role=button[name=Buscar]"
    except Exception:
        pass

    button_selectors = [
        'button[type="submit"]',
        'button',
        'input[type="submit"]',
    ]

    for selector in button_selectors:
        try:
            loc = page.locator(selector)
            n = loc.count()
            for i in range(n):
                item = loc.nth(i)
                txt = ""
                try:
                    txt = (item.inner_text() or "").strip().lower()
                except Exception:
                    pass

                value_attr = ""
                try:
                    value_attr = (item.get_attribute("value") or "").strip().lower()
                except Exception:
                    pass

                blob = f"{txt} {value_attr}".lower()
                if selector == 'button[type="submit"]' or "buscar" in blob:
                    return item, f"{selector}[{i}]"
        except Exception:
            pass

    raise RuntimeError("No se encontró el botón Buscar.")


def uncheck_auto_filter(page):
    try:
        page.wait_for_timeout(1000)

        auto_candidates = [
            'input[id="prov_tipo|auto"]',
            'input[id*="auto" i]',
            'input[type="checkbox"]'
        ]

        for selector in auto_candidates:
            try:
                loc = page.locator(selector)
                count = loc.count()

                for i in range(count):
                    item = loc.nth(i)
                    try:
                        item_id = (item.get_attribute("id") or "").lower()
                        name = (item.get_attribute("name") or "").lower()
                        aria = (item.get_attribute("aria-label") or "").lower()

                        blob = f"{item_id} {name} {aria}"
                        if selector == 'input[type="checkbox"]' and "auto" not in blob:
                            continue

                        if item.is_checked():
                            item.uncheck()
                            page.wait_for_timeout(1200)
                            log(f"Filtro Auto desmarcado con selector: {selector}")
                            return True
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            labels = page.locator("label")
            n = labels.count()
            for i in range(n):
                lbl = labels.nth(i)
                try:
                    txt = lbl.inner_text().strip().lower()
                    if txt == "auto" or txt.startswith("auto"):
                        lbl.click()
                        page.wait_for_timeout(1200)
                        log("Filtro Auto desmarcado por label")
                        return True
                except Exception:
                    pass
        except Exception:
            pass

        log("No se encontró o no fue necesario desmarcar Auto.")
        return False

    except Exception as e:
        log(f"Error al desmarcar Auto: {e}")
        return False


def open_search_and_query(page, query):
    page.goto(SEARCH_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    title = page.title()
    content = page.content()

    if "blocked" in title.lower() or "blocked" in content.lower():
        debug = dump_debug_page(page, "blocked_search_page")
        raise RuntimeError(f"Acceso bloqueado. Title='{title}'. Debug={debug}")

    search_input, selector_used = find_search_input(page)
    log(f"Selector usado para input: {selector_used}")

    search_input.click()
    page.wait_for_timeout(300)

    try:
        search_input.fill("")
    except Exception:
        pass

    search_input.fill(query)
    page.wait_for_timeout(1000)

    uncheck_auto_filter(page)

    dump_debug_page(page, "before_click_search")

    search_button, button_selector = find_search_button(page)
    log(f"Selector usado para botón: {button_selector}")

    search_button.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)

    dump_debug_page(page, "after_click_search")


def parse_result_page(page, query, page_num):
    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    results = []
    table = soup.select_one("table#tabla-resultado")

    if table:
        rows = table.select("tbody tr")
    else:
        rows = soup.find_all(["article", "tr", "div"])

    for idx, row in enumerate(rows, start=1):
        text = row.get_text(" ", strip=True)

        if not text or len(text) < 20:
            continue

        anchors = row.find_all("a", href=True)
        if not anchors:
            continue

        main_anchor = None
        for a in anchors:
            href = a.get("href", "")
            txt = a.get_text(" ", strip=True)
            if "/relatoria/" in href or re.search(r"[A-Z]{1,3}\.?\-?\d+/\d+|[A-Z]{1,3}\-\d+\-\d+", txt):
                main_anchor = a
                break

        if not main_anchor:
            main_anchor = anchors[0]

        detalle_url = absolutize(main_anchor.get("href"))
        titulo_lista = main_anchor.get_text(" ", strip=True)

        if is_auto_record(titulo_lista):
            continue

        if is_auto_record(text):
            continue

        ficha_url = None
        for a in anchors:
            href = a.get("href", "")
            txt = a.get_text(" ", strip=True).lower()
            if "ficha" in txt or "ficha" in href.lower():
                ficha_url = absolutize(href)
                break

        fecha_providencia = None
        fecha_publicacion = None

        m1 = re.search(r"Fecha de providencia\s+(\d{4}-\d{2}-\d{2})", text)
        if m1:
            fecha_providencia = m1.group(1)

        m2 = re.search(r"Fecha de publicación\s+(\d{4}-\d{2}-\d{2})", text)
        if m2:
            fecha_publicacion = m2.group(1)

        results.append({
            "query": query,
            "page_num": page_num,
            "row_num": idx,
            "titulo_lista": titulo_lista,
            "detalle_url": detalle_url,
            "ficha_url": ficha_url,
            "fecha_providencia": fecha_providencia,
            "fecha_publicacion": fecha_publicacion,
            "texto_lista": text,
        })

    cleaned = []
    seen = set()
    for r in results:
        key = r["detalle_url"]
        if key and key not in seen:
            cleaned.append(r)
            seen.add(key)

    return cleaned


def go_next_page(page):
    try:
        candidates = page.locator("a, button").all()
        for cand in candidates:
            try:
                txt = cand.inner_text().strip()
                if txt == ">":
                    cand.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2500)
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def scrape_query(query, max_pages=2):
    p, browser = launch_browser()
    rows = []

    try:
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(90000)

        open_search_and_query(page, query)

        for page_num in range(1, max_pages + 1):
            page_rows = parse_result_page(page, query, page_num)
            log(f"Query='{query}' | página={page_num} | resultados={len(page_rows)}")

            if not page_rows:
                dump_debug_page(page, f"empty_results_page_{page_num}")
                break

            rows.extend(page_rows)

            moved = go_next_page(page)
            if not moved:
                break

        df = pd.DataFrame(rows)
        if not df.empty:
            df.drop_duplicates(subset=["detalle_url"], inplace=True)

        return df

    finally:
        browser.close()
        p.stop()


def scrape_detail_page(page, detalle_url):
    page.goto(detalle_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    page_title = page.title()
    h1 = soup.find("h1")
    titulo_ficha = h1.get_text(" ", strip=True) if h1 else page_title

    if is_auto_record(titulo_ficha) or is_auto_record(page_title):
        return {
            "detalle_url": detalle_url,
            "page_title": page_title,
            "titulo_ficha": titulo_ficha,
            "excluded_reason": "auto_detected",
            "doc_url": None,
            "doc_ext": None,
            "doc_path": None,
            "texto_extraido_len": None,
        }

    doc_url = None
    doc_ext = None

    for a in soup.find_all("a", href=True):
        href = absolutize(a["href"])
        ext = file_ext_from_url(href)
        if ext in [".pdf", ".rtf", ".htm", ".html", ".doc", ".docx"]:
            doc_url = href
            doc_ext = ext
            break

    if doc_url:
        stem = Path(urlparse(doc_url).path).stem
        if is_auto_record(stem):
            return {
                "detalle_url": detalle_url,
                "page_title": page_title,
                "titulo_ficha": titulo_ficha,
                "excluded_reason": "auto_document",
                "doc_url": doc_url,
                "doc_ext": doc_ext,
                "doc_path": None,
                "texto_extraido_len": None,
            }

    slug = clean_filename(titulo_ficha or detalle_url.split("/")[-1])

    doc_path = None
    if doc_url and doc_ext:
        doc_path = DOC_DIR / f"{slug}{doc_ext}"
        if not doc_path.exists():
            save_binary(doc_url, doc_path)

    text_visible = soup.get_text("\n", strip=True)

    return {
        "detalle_url": detalle_url,
        "page_title": page_title,
        "titulo_ficha": titulo_ficha,
        "excluded_reason": None,
        "doc_url": doc_url,
        "doc_ext": doc_ext,
        "doc_path": str(doc_path) if doc_path else None,
        "texto_extraido_len": len(text_visible),
    }


def scrape_sentence_list(urls):
    p, browser = launch_browser()
    records = []

    try:
        page = browser.new_page(viewport={"width": 1400, "height": 2000})
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(90000)

        for url in urls:
            try:
                rec = scrape_detail_page(page, url)
                records.append(rec)
                polite_sleep(1.0, 2.0)
            except Exception as e:
                records.append({
                    "detalle_url": url,
                    "page_title": None,
                    "titulo_ficha": None,
                    "excluded_reason": None,
                    "doc_url": None,
                    "doc_ext": None,
                    "doc_path": None,
                    "texto_extraido_len": None,
                    "error_detail": str(e),
                })

        return pd.DataFrame(records)

    finally:
        browser.close()
        p.stop()


def run_smoke():
    out = smoke_test_search()
    print(json.dumps(out, ensure_ascii=False, indent=2))


def run_query_mode():
    queries_path = META_DIR / "queries_input.json"
    if not queries_path.exists():
        raise FileNotFoundError(f"No existe {queries_path}")

    with open(queries_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    queries = payload.get("queries", [])
    max_pages = int(payload.get("max_pages", 2))

    all_dfs = []
    query_errors = []

    for q in queries:
        log(f"Ejecutando query: {q}")
        try:
            df_q = scrape_query(q, max_pages=max_pages)
            if not df_q.empty:
                df_q["query_source"] = q
                all_dfs.append(df_q)
        except Exception as e:
            err = {"query": q, "error": str(e)}
            query_errors.append(err)
            log(f"Error con query '{q}': {e}")

    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)
        df_all.drop_duplicates(subset=["detalle_url"], inplace=True)
    else:
        df_all = pd.DataFrame()

    out_csv = META_DIR / "indice_resultados.csv"
    out_json = META_DIR / "indice_resultados.json"
    err_json = META_DIR / "query_errors.json"

    df_all.to_csv(out_csv, index=False)
    df_all.to_json(out_json, orient="records", force_ascii=False, indent=2)
    save_json(query_errors, err_json)

    log(f"Guardado: {out_csv}")
    log(f"Guardado: {out_json}")
    log(f"Guardado: {err_json}")
    log(f"Total resultados: {len(df_all)}")


def run_urls_mode():
    urls_csv = META_DIR / "urls_input.csv"
    if not urls_csv.exists():
        raise FileNotFoundError(f"No existe {urls_csv}")

    df_urls = pd.read_csv(urls_csv)
    if "detalle_url" not in df_urls.columns:
        raise ValueError("urls_input.csv debe tener columna 'detalle_url'")

    urls = df_urls["detalle_url"].dropna().astype(str).tolist()
    df = scrape_sentence_list(urls)

    out_csv = META_DIR / "descarga_sentencias.csv"
    out_json = META_DIR / "descarga_sentencias.json"

    df.to_csv(out_csv, index=False)
    df.to_json(out_json, orient="records", force_ascii=False, indent=2)

    log(f"Guardado: {out_csv}")
    log(f"Guardado: {out_json}")
    log(f"Total URLs procesadas: {len(df)}")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "query", "urls"], required=True)
    args = parser.parse_args()

    if args.mode == "smoke":
        run_smoke()
    elif args.mode == "query":
        run_query_mode()
    elif args.mode == "urls":
        run_urls_mode()


if __name__ == "__main__":
    main()