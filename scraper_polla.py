"""
scraper_polla.py
================
1. Extrae fechas y horas del panel Admin.
2. Extrae la tabla de "Resumen" (Escáner Multi-Línea y Single-Line).
3. Extrae las "Predicciones" detalladas.
4. Genera banderas para Google Sheets (=IMAGE) y genera un 'datos.json' para la Web.
"""

import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

# ── Credenciales ──────────────────────────────────────────────────────────────
EMAIL    = "pabloflh@hotmail.com"
PASSWORD = "Palelo2902"

# ── Participantes y Admin ─────────────────────────────────────────────────────
ADMIN_URL = "https://www.pollamundial.org/dashboard/grupo/-Otfg7UCP0e58wU243RP/admin"
BASE = "https://www.pollamundial.org/dashboard/grupo/-Otfg7UCP0e58wU243RP/table/user"
PARTICIPANTES = [
    ("Lindsay",   f"{BASE}/A0Zo5BJqfBU18jYxe5fj2TRLVSP2/L5zaBqs5Ngy3Y7ClhWlq"),
    ("Angelica",  f"{BASE}/2zn7xdPdY9UTvrIFITXzJ5eQIeq1/mW3Vwq5Ljy7FhIZ0wCLc"),
    ("Samuel",    f"{BASE}/2JdIIDlkoActqKmBlGeHfTjK5N92/mIvyqrVv4x2F9GKxTBMD"),
    ("Marcela",   f"{BASE}/IjA0sxTW7xMeabb8pnrqeexFByv1/zEmbzARM85ZuM230EsTg"),
    ("Mauricio",  f"{BASE}/G1qc49vgbgNyJ3IveffWypjEH5D2/q1j35hB2RyvnQmtXXUwY"),
    ("Julian",    f"{BASE}/yeocrRmIvydLB6dQDwioJXdXTSC3/gTxYn26dtcadGwNeQp4A"),
    ("Pablo",     f"{BASE}/WAgoPj3jfTSF0y3XFadwpGpJP602/-Otfg7UCP0e58wU243RQ"),
    ("Jorge",     f"{BASE}/C5VUhimGjBNDZJYW9ZXIciz2Kro2/cMIGb5ORuuNg93bGQdVg"),
    ("Cesar",     f"{BASE}/DI9vh4EW67R6H3vYDRTck9r59ND2/Eu1DfomJv3u0FDm7VSRr"),
    ("Margarita", f"{BASE}/itbQANbGu1dvygD3jMEyAF4MncJ2/RJzeNgr86v2tOuRszwCB"),
    ("Yoshi",     f"{BASE}/kGdAD9aFtSbWq1tDqR5Xm9WEvkX2/HKsa5Wh6wQky9A5YLEkE"),
    ("Gabriel",   f"{BASE}/aWcdqyw6Nid3RW6LZlQLZFpMTf93/hiPQnB4Snsne75iztav3"),
]

# ── Diccionarios de Traducción y Banderas CDN ─────────────────────────────────
NAME_TO_CODE = {
    "México": "MEX", "Canadá": "CAN", "Estados Unidos": "USA", "Argentina": "ARG", 
    "Colombia": "COL", "Perú": "PER", "Chile": "CHI", "Ecuador": "ECU", 
    "Venezuela": "VEN", "Jamaica": "JAM", "Bolivia": "BOL", "Uruguay": "URU", 
    "Panamá": "PAN", "Brasil": "BRA", "Costa Rica": "CRC", "Paraguay": "PAR",
    "Curazao": "CUR", "Curaçao": "CUR", "Alemania": "GER", "Escocia": "SCO", 
    "Hungría": "HUN", "Suiza": "SUI", "España": "ESP", "Croacia": "CRO", 
    "Italia": "ITA", "Albania": "ALB", "Eslovenia": "SVN", "Dinamarca": "DEN", 
    "Serbia": "SRB", "Inglaterra": "ENG", "Polonia": "POL", "Países Bajos": "NED", 
    "Holanda": "NED", "Austria": "AUT", "Francia": "FRA", "Bélgica": "BEL", 
    "Eslovaquia": "SVK", "Rumania": "ROU", "Ucrania": "UKR", "Turquía": "TUR", 
    "Georgia": "GEO", "Portugal": "POR", "República Checa": "CZE", 
    "Bosnia y Herzegovina": "BIH", "Gales": "WAL", "Suecia": "SWE", "Noruega": "NOR",
    "Catar": "QAT", "Qatar": "QAT", "Corea del Sur": "KOR", "Japón": "JPN", 
    "Irán": "IRN", "Iran": "IRN", "Arabia Saudita": "KSA", "Australia": "AUS",
    "Irak": "IRQ", "Iraq": "IRQ", "Jordania": "JOR", "Sudáfrica": "RSA", 
    "Sudafrica": "RSA", "Egipto": "EGY", "Senegal": "SEN", "Túnez": "TUN", 
    "Marruecos": "MAR", "Camerún": "CMR", "Ghana": "GHA", "Cabo Verde": "CPV", 
    "Costa de Marfil": "CIV", "Argelia": "ALG", "RD Congo": "COD", 
    "República Democrática del Congo": "COD", "Congo": "COD", "Nueva Zelanda": "NZL",
    "EGY": "EGY", "IRN": "IRN", "MEX": "MEX", "ARG": "ARG", "COL": "COL", "RSA": "RSA"
}

FLAGS_CDN = {
    "MEX": "mx", "KOR": "kr", "CZE": "cz", "CAN": "ca", "BIH": "ba", "QAT": "qa", 
    "SUI": "ch", "ARG": "ar", "COL": "co", "PER": "pe", "CHI": "cl", "ECU": "ec", 
    "VEN": "ve", "JAM": "jm", "USA": "us", "BOL": "bo", "URU": "uy", "PAN": "pa", 
    "BRA": "br", "CRC": "cr", "PAR": "py", "GER": "de", "SCO": "gb-sct", "HUN": "hu", 
    "ESP": "es", "CRO": "hr", "ITA": "it", "ALB": "al", "SVN": "si", "DEN": "dk", 
    "SRB": "rs", "ENG": "gb-eng", "POL": "pl", "NED": "nl", "AUT": "at", "FRA": "fr", 
    "BEL": "be", "SVK": "sk", "ROU": "ro", "UKR": "ua", "TUR": "tr", "GEO": "ge", 
    "POR": "pt", "EGY": "eg", "IRN": "ir", "SEN": "sn", "TUN": "tn", "MAR": "ma", 
    "CMR": "cm", "GHA": "gh", "KSA": "sa", "JPN": "jp", "AUS": "au", "WAL": "gb-wls", 
    "NZL": "nz", "CPV": "cv", "IRQ": "iq", "SWE": "se", "CUR": "cw", "CIV": "ci", 
    "RSA": "za", "COD": "cd", "JOR": "jo", "ALG": "dz", "NOR": "no"
}

# ── Config ────────────────────────────────────────────────────────────────────
LOGIN_URL  = "https://www.pollamundial.org/"
WAIT_MS    = 15_000
OUTPUT_DIR = Path("polla_output")
PROFILE    = Path("playwright_profile")

# ── Regex ─────────────────────────────────────────────────────────────────────
RE_FASE      = re.compile(r"Fase:\s*(.+)")
RE_RESULTADO = re.compile(r"([A-Z]{2,4})\s+(\d+)\s*-\s*(\d+)\s+([A-Z]{2,4})")
RE_PRED      = re.compile(r"Predicci[oó]n:\s*(\d+)\s*-\s*(\d+)", re.I)
RE_TOTAL     = re.compile(r"Puntaje:\s*(\d+)", re.I)

# ─────────────────────────────────────────────────────────────────────────────

def close_ads(page: Page) -> None:
    try: page.keyboard.press("Escape")
    except: pass
    close_sels = ['.btn-close', 'button:has-text("Cerrar")', 'button:has-text("Close")']
    for sel in close_sels:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=300): btn.click(timeout=500)
        except: pass

def login(page: Page) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=WAIT_MS)
    email_sel = 'input[type="email"], input[placeholder*="correo" i]'
    if not page.locator(email_sel).first.is_visible(timeout=3_000): return
    print("  -> Haciendo login...")
    page.locator(email_sel).first.fill(EMAIL)
    page.locator('input[type="password"]').first.fill(PASSWORD)
    try: page.locator('button[type="submit"], input[type="submit"]').first.click(timeout=5_000)
    except: page.keyboard.press("Enter")
    try: page.wait_for_load_state("networkidle", timeout=WAIT_MS)
    except PWTimeout: pass


def parse_dt(date_str: str, time_str: str) -> datetime:
    if not date_str or date_str == "Sin Fecha": return datetime.max
    meses = {"Ene":1, "Jan":1, "Feb":2, "Mar":3, "Abr":4, "Apr":4, "May":5, "Jun":6, "Jul":7, "Ago":8, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dic":12, "Dec":12}
    try:
        parts = date_str.split()
        mes_str = parts[0][:3].capitalize()
        m = meses.get(mes_str, 1)
        d = int(parts[1])
        hr, mn = 0, 0
        if time_str and time_str != "Sin Hora":
            tparts = time_str.split(":")
            hr, mn = int(tparts[0]), int(tparts[1])
        return datetime(2026, m, d, hr, mn) 
    except Exception: return datetime.max


def scrape_admin_partidos(page: Page) -> dict:
    fechas_dict = {}
    print(f"\n[2] Obteniendo Fechas y Horas del panel Admin...")
    try:
        page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=WAIT_MS)
        time.sleep(3)
        close_ads(page)

        try: page.locator("text=/Partidos/i").first.click(timeout=5000)
        except: pass
        time.sleep(3)

        text = page.evaluate("() => document.body.innerText")
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        current_date = "Sin Fecha"
        buffer = []
        re_mes_dia = re.compile(r"^(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic|Jan|Apr|Aug|Dec)\s+\d{1,2}$", re.I)
        re_num_date = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")

        for line in lines:
            if line in ["Partidos", "Seleccionar Todos"] or line.startswith("Grupo") or line == "": continue
            if re_mes_dia.match(line) or re_num_date.match(line):
                current_date = line
                continue
            if re.match(r"^\d{1,2}:\d{2}$", line):
                time_str = line
                t1_raw = buffer.pop() if buffer else "Unknown"
                if " vs " in t1_raw or " - " in t1_raw:
                    sep = " vs " if " vs " in t1_raw else " - "
                    parts = t1_raw.split(sep)
                    t1 = parts[0].strip(); t2 = parts[1].strip()
                else:
                    t2 = t1_raw; t1 = buffer.pop() if buffer else "Unknown"
                cod1 = NAME_TO_CODE.get(t1, t1[:3].upper())
                cod2 = NAME_TO_CODE.get(t2, t2[:3].upper())
                fechas_dict[(cod1, cod2)] = {"fecha": current_date, "hora": time_str}
                fechas_dict[(cod2, cod1)] = {"fecha": current_date, "hora": time_str}
                buffer.clear()
            else:
                buffer.append(line)
        print(f"  -> Se obtuvieron fechas para {len(fechas_dict)//2} partidos.")
    except Exception as e: print(f"  x Error obteniendo fechas de Admin: {e}")
    return fechas_dict


def scrape_resumen(page: Page, nombre: str) -> list[dict]:
    rows = []
    try:
        page.wait_for_function("() => document.body.innerText.includes('Aciertos')", timeout=8_000)
        time.sleep(0.5) 
    except PWTimeout:
        print("         ! No se encontró la tabla de Resumen a tiempo.")
        return rows

    text = page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    re_aciertos = re.compile(r"^\d+(?:\s*\(\d+/\d+\))?$")
    re_numero = re.compile(r"^\d+$")
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if "PUNTAJE TOTAL" in line.upper(): break
        if line.upper() in ["CONCEPTO", "ACIERTOS", "REGLA", "SUBTOTAL"]:
            i += 1
            continue

        m = re.search(r"^(.*?)\s+(\d+(?:\s*\(\d+/\d+\))?)\s+(\d+)\s+(\d+)$", line)
        if m and not re_numero.match(m.group(1)):
            rows.append({
                "Participante": nombre, "Concepto": m.group(1).strip(),
                "Aciertos": m.group(2).strip(), "Regla": m.group(3).strip(), "Subtotal": m.group(4).strip()
            })
            i += 1
            continue
        
        if i + 3 < len(lines):
            c2, c3, c4 = lines[i+1], lines[i+2], lines[i+3]
            if re_aciertos.match(c2) and re_numero.match(c3) and re_numero.match(c4):
                if not re_numero.match(line) and "BONOS" not in line.upper() and "RESULTADOS" not in line.upper():
                    rows.append({
                        "Participante": nombre, "Concepto": line,
                        "Aciertos": c2, "Regla": c3, "Subtotal": c4
                    })
                    i += 4
                    continue
        i += 1
    return rows


def scrape_predicciones(page: Page, nombre: str) -> tuple[list[dict], str]:
    try:
        btn = page.get_by_text("Detalles", exact=True).last
        btn.click(timeout=3_000)
        time.sleep(2) 
        if "#google_vignette" in page.url:
            page.go_back()
            time.sleep(1.5)
        page.wait_for_function("() => document.body.innerText.includes('Predicci')", timeout=5_000)
    except: return [], "?"

    text = page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    total_pts = next((RE_TOTAL.search(l).group(1) for l in lines if RE_TOTAL.search(l)), "?")

    rows = []
    fase = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        m_fase = RE_FASE.search(line)
        if m_fase:
            fase = m_fase.group(1).strip()
            i += 1; continue

        m_res = RE_RESULTADO.match(line)
        if m_res:
            local_cod = m_res.group(1); local_gol = m_res.group(2)
            visit_gol = m_res.group(3); visit_cod = m_res.group(4)
            resultado = f"{local_gol}-{visit_gol}"
            pred = ""
            for j in range(i + 1, min(i + 8, len(lines))):
                m_pred = RE_PRED.search(lines[j])
                if m_pred:
                    pred = f"{m_pred.group(1)}-{m_pred.group(2)}"; break

            rows.append({
                "fase": fase, "local_cod": local_cod, "visit_cod": visit_cod,
                "resultado": resultado, "prediccion": pred, "participante": nombre
            })
        i += 1
    return rows, total_pts

# ─────────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PROFILE.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_preds: list[dict] = []
    all_resumen: list[dict] = []
    totales_global = {}
    nombres = [n for n, _ in PARTICIPANTES]

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        def block_ad_networks(route):
            ad_domains = ["googlesyndication", "doubleclick", "adservice.google", "googleads"]
            if any(domain in route.request.url for domain in ad_domains): route.abort()
            else: route.continue_()

        ctx.route("**/*", block_ad_networks)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("\n[1] Login...")
        login(page)
        fechas_dict = scrape_admin_partidos(page)

        print(f"\n[3] Scrapeando Resumen y Detalles de {len(PARTICIPANTES)} participantes...\n")
        for idx, (nombre, url) in enumerate(PARTICIPANTES, 1):
            print(f"  [{idx}/{len(PARTICIPANTES)}] {nombre}...")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=WAIT_MS)
                close_ads(page)
                res_data = scrape_resumen(page, nombre)
                all_resumen.extend(res_data)
                pred_data, total = scrape_predicciones(page, nombre)
                all_preds.extend(pred_data)
                totales_global[nombre] = total
                
                if pred_data: print(f"         -> Resumen: {len(res_data)} items | Preds: {len(pred_data)} partidos | Total: {total} pts")
                else: print(f"         ! Error leyendo detalles de este usuario.")
            except Exception as e: print(f"         x Error general: {e}")
            time.sleep(1)
        ctx.close()

    print(f"\n[4] Generando archivos...\n")

    partidos: dict[tuple, dict] = {}
    for row in all_preds:
        loc = row["local_cod"]
        vis = row["visit_cod"]
        key = (row["fase"], loc, vis)
        
        if key not in partidos:
            dt_info = fechas_dict.get((loc, vis), {"fecha": "Sin Fecha", "hora": "Sin Hora"})
            cod_loc = FLAGS_CDN.get(loc, "")
            cod_vis = FLAGS_CDN.get(vis, "")
            
            # Formatos para Excel
            img_loc_excel = f'=IMAGE("https://flagcdn.com/24x18/{cod_loc}.png")' if cod_loc else ""
            img_vis_excel = f'=IMAGE("https://flagcdn.com/24x18/{cod_vis}.png")' if cod_vis else ""
            
            # Formatos limpios para la Web (JSON)
            url_loc_web = f"https://flagcdn.com/24x18/{cod_loc}.png" if cod_loc else ""
            url_vis_web = f"https://flagcdn.com/24x18/{cod_vis}.png" if cod_vis else ""

            partidos[key] = {
                "Fecha": dt_info["fecha"], "Hora": dt_info["hora"], "Fase": row["fase"],
                "Bandera L": img_loc_excel, "Local": loc, "Bandera V": img_vis_excel, "Visitante": vis,
                "Marcador": row["resultado"], "_dt_obj": parse_dt(dt_info["fecha"], dt_info["hora"]),
                "_url_l": url_loc_web, "_url_v": url_vis_web
            }
            for n in nombres: partidos[key][n] = ""
        
        partidos[key][row["participante"]] = row["prediccion"]
        if row["resultado"]: partidos[key]["Marcador"] = row["resultado"]

    lista_partidos = list(partidos.values())
    lista_partidos.sort(key=lambda x: x["_dt_obj"])

    # --- EXPORTAR TSVs PARA EXCEL ---
    #cols_pred = ["Fecha", "Hora", "Fase", "Bandera L", "Local", "Bandera V", "Visitante", "Marcador"] + nombres
    #with (OUTPUT_DIR / f"predicciones_{ts}.tsv").open("w", newline="", encoding="utf-8-sig") as f:
    #    w = csv.DictWriter(f, fieldnames=cols_pred, delimiter="\t", extrasaction="ignore")
    #    w.writeheader()
    #    w.writerows(lista_partidos)

    #if all_resumen:
    #    cols_res = ["Participante", "Concepto", "Aciertos", "Regla", "Subtotal"]
    #    with (OUTPUT_DIR / f"resumen_{ts}.tsv").open("w", newline="", encoding="utf-8-sig") as f:
    #        w = csv.DictWriter(f, fieldnames=cols_res, delimiter="\t")
    #        w.writeheader()
    #        w.writerows(all_resumen)

    # --- EXPORTAR JSON PARA LA WEB ---
    totales_lista = [{"Participante": n, "Total": totales_global.get(n, "0")} for n in nombres]
    # Ordenar posiciones de mayor a menor
    totales_lista.sort(key=lambda x: int(x["Total"]) if str(x["Total"]).isdigit() else 0, reverse=True)

    json_predicciones = []
    for p in lista_partidos:
        # Copiar limpio sin las fórmulas de Excel
        p_clean = {
            "Fecha": p["Fecha"], "Hora": p["Hora"], "Fase": p["Fase"],
            "Local": p["Local"], "FlagLocal": p["_url_l"],
            "Visitante": p["Visitante"], "FlagVisitante": p["_url_v"],
            "Marcador": p["Marcador"]
        }
        for n in nombres: p_clean[n] = p[n]
        json_predicciones.append(p_clean)

    data_json = {
        "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nombres": nombres,
        "totales": totales_lista,
        "resumen": all_resumen,
        "predicciones": json_predicciones
    }

    with (OUTPUT_DIR / "datos.json").open("w", encoding="utf-8") as f:
        json.dump(data_json, f, ensure_ascii=False, indent=2)

    print(f"\n¡Todo listo! Los TSV y el archivo 'datos.json' están en '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    main()
