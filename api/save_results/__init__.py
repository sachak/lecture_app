# tout en haut du fichier
logging.basicConfig(level=logging.INFO)

…

# juste après rows_main =
rows_main = [r for r in data if r.get("phase") != "practice"]
logging.info("Reçu %s lignes, dont %s lignes test",
             len(data), len(rows_main))

…

# juste après cnx.commit()
logging.info("INSERT OK – %s lignes écrites en SQL", len(rows_main))

…

# juste avant buf = io.BytesIO()
logging.info("Calcul stats : %s colonnes numériques, %s lignes",
             len(num_cols), len(df))

…

# juste après cnt.upload_blob(...)
logging.info("Blob %s_results.xlsx uploadé dans %s",
             pid, STO_CONT)

import os, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── variables d’environnement ──────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")                   # chaîne ODBC
API_SECRET = os.getenv("API_SECRET")                 # header x-api-secret
STO_CONN   = os.getenv("STORAGE_CONN")               # chaîne connexion Storage
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results")

# ─── helpers ────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    if n in (4, 5): return "4_5"
    if n in (6, 7): return "6_7"
    if n in (8, 9): return "8_9"
    return "10_11"

def http_resp(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        })

# ─── Function entry point ───────────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    if req.method == "OPTIONS":
        return http_resp(204)

    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return http_resp(403, "Forbidden")

    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return http_resp(400, f"Invalid JSON : {exc}")

    if not data or "participant" not in data[0]:
        return http_resp(400, "participant missing")

    pid = str(data[0]["participant"]).strip() or "anon"

    # ─── 1. Lignes test uniquement ─────────────────────────────────────
    rows_main = [r for r in data if r.get("phase") != "practice"]

    # ─── 2. INSERTION SQL ──────────────────────────────────────────────
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in rows_main:
                cur.execute(
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase,
                       participant, groupe, nblettres)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    r.get("word", ""),
                    int(r.get("rt_ms", 0)),
                    r.get("response", ""),
                    r.get("phase", ""),
                    r.get("participant", ""),
                    r.get("groupe", ""),
                    r.get("nblettres"))
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL insert")
        return http_resp(500, f"DB error : {exc}")

    # ─── 3. STATISTIQUES ───────────────────────────────────────────────
    df = pd.DataFrame(rows_main)
    if df.empty:                    # seulement practice
        return http_resp(200, "OK (practice only)")

    if "nblettres" not in df.columns:
        logging.warning("nblettres absent ; stats ignorées.")
        return http_resp(200, "OK (saved)")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    META = {"word","response","phase","participant","groupe","letters_block"}
    num  = [c for c in df.columns
            if c not in META and pd.api.types.is_numeric_dtype(df[c])]

    g_grp = df.groupby("groupe")
    stats_grp = g_grp[num].agg(['mean','std'])
    stats_grp.insert(0, 'n', g_grp.size())
    stats_grp = stats_grp.reset_index()
    stats_grp.columns = [(c if isinstance(c,str)
                          else f"{c[0]}_{'mean' if c[1]=='mean' else 'sd'}")
                         for c in stats_grp.columns]

    g_blk = df.groupby("letters_block")
    stats_blk = g_blk[num].agg(['mean','std'])
    stats_blk.insert(0, 'n', g_blk.size())
    stats_blk = stats_blk.reset_index()
    stats_blk.columns = [(c if isinstance(c,str)
                          else f"{c[0]}_{'mean' if c[1]=='mean' else 'sd'}")
                         for c in stats_blk.columns]

    # ─── 4. Excel en mémoire ───────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel       (wr, "tirage"         , index=False)
        stats_grp.to_excel(wr, "Stats_ByGroup"  , index=False)
        stats_blk.to_excel(wr, "Stats_ByLetters", index=False)
    buf.seek(0)

    # ─── 5. Upload Blob ────────────────────────────────────────────────
    try:
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            name            = f"{pid}_results.xlsx",
            data            = buf.getvalue(),
            overwrite       = True,
            content_settings=ContentSettings(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        )
    except Exception as exc:
        logging.exception("Blob upload")
        return http_resp(500, f"Blob error : {exc}")

    return http_resp(200, "OK")
