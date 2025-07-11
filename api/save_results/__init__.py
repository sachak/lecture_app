import os, io, json, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── variables d’environnement ──────────────────────────────────────────
SQL_CONN    = os.getenv("SQL_CONN")                  # chaîne ODBC
API_SECRET  = os.getenv("API_SECRET")                # header x-api-secret
STO_CONN    = os.getenv("STORAGE_CONN")              # chaîne connexion Storage
STO_CONT    = os.getenv("STORAGE_CONTAINER", "results")

# ─── helpers ────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"

def http_resp(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
          "Access-Control-Allow-Origin":"*",
          "Access-Control-Allow-Methods":"POST,OPTIONS",
          "Access-Control-Allow-Headers":"Content-Type,x-api-secret"
        })

# ─── Function entry point (v1) ──────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    # CORS pré-vol
    if req.method == "OPTIONS":
        return http_resp(204)

    # Secret
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return http_resp(403, "Forbidden")

    # Lecture JSON
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return http_resp(400, f"Invalid JSON : {exc}")

    if not data or "participant" not in data[0]:
        return http_resp(400, "participant missing")

    pid = str(data[0]["participant"]).strip() or "anon"

    # ─── insertion SQL ────────────────────────────────────────────────
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute(
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase,
                       participant, groupe, nblettres)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    r.get("word",""),
                    int(r.get("rt_ms",0)),
                    r.get("response",""),
                    r.get("phase",""),
                    r.get("participant",""),
                    r.get("groupe",""),
                    r.get("nblettres")
                )
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL insert")
        return http_resp(500, f"DB error : {exc}")

    # ─── création DataFrame hors practice ─────────────────────────────
    df = pd.DataFrame(data)
    df = df[df.phase != "practice"].copy()
    if df.empty:
        return http_resp(200, "OK (practice only)")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    stats_grp = (df.groupby("groupe")["rt_ms"]
                   .agg(['count','mean','std']).reset_index()
                   .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    stats_blk = (df.groupby("letters_block")["rt_ms"]
                   .agg(['count','mean','std']).reset_index()
                   .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    # ─── Excel en mémoire ─────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel      (wr, sheet_name="tirage",          index=False)
        stats_grp.to_excel(wr, sheet_name="Stats_ByGroup",   index=False)
        stats_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)
    buf.seek(0)

    # ─── upload Blob  (un fichier par participant) ───────────────────
    try:
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            name = f"{pid}_results.xlsx",
            data = buf.getvalue(),
            overwrite = True,
            content_settings = ContentSettings(
              content_type=("application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"))
        )
    except Exception as exc:
        logging.exception("Blob upload")
        return http_resp(500, f"Blob error : {exc}")

    return http_resp(200, "OK")
