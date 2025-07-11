# =============================================================
# save_results  – model v1 (Static Web Apps)
# 1) insère word / rt_ms / response / phase / participant
# 2) génère un classeur Excel (tirage + stats) pour CE participant
# 3) dépose PID_results.xlsx dans le conteneur Blob STORAGE_CONTAINER
# =============================================================

import os, json, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ---------- variables d’environnement ------------------------
SQL_CONN    = os.getenv("SQL_CONN")                 # chaîne ODBC
API_SECRET  = os.getenv("API_SECRET")               # header facultatif
STO_CONN    = os.getenv("STORAGE_CONN")             # connexion Blob
STO_CONT    = os.getenv("STORAGE_CONTAINER", "results")

# ---------- utils --------------------------------------------
def letters_block(n: int) -> str:
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"

def resp(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
            "Access-Control-Allow-Origin":"*",
            "Access-Control-Allow-Methods":"POST,OPTIONS",
            "Access-Control-Allow-Headers":"Content-Type,x-api-secret"
        })

# ---------- MAIN ---------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    # CORS pre-flight -------------------------------------------------------
    if req.method == "OPTIONS":
        return resp(204)

    # Secret ---------------------------------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return resp(403, "Forbidden")

    # Lecture JSON ---------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as e:
        return resp(400, f"Invalid JSON : {e}")

    if not data or "participant" not in data[0]:
        return resp(400, "participant field missing")
    pid = str(data[0]["participant"]).strip() or "anon"

    # Insertion SQL --------------------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute(
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase, participant,
                       groupe, nblettres)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    r.get("word",        ""),
                    int(r.get("rt_ms", 0)),
                    r.get("response",    ""),
                    r.get("phase",       ""),
                    r.get("participant", ""),
                    r.get("groupe",      ""),
                    r.get("nblettres")
                )
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL error")
        return resp(500, f"DB error : {exc}")

    # DataFrame pour Excel (on retire practice) ----------------------------
    df = pd.DataFrame(data)
    df = df[df.phase != "practice"].copy()
    if df.empty:
        return resp(200, "OK (practice only)")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    # Stats ByGroup
    stat_grp = (df.groupby("groupe")["rt_ms"]
                  .agg(['count', 'mean', 'std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    # Stats ByLetters
    stat_blk = (df.groupby("letters_block")["rt_ms"]
                  .agg(['count', 'mean', 'std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    # Génération classeur Excel -------------------------------------------
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel      (wr, sheet_name="tirage",        index=False)
        stat_grp.to_excel(wr, sheet_name="Stats_ByGroup", index=False)
        stat_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)
    buf.seek(0)

    # Upload vers Blob -----------------------------------------------------
    try:
        bs   = BlobServiceClient.from_connection_string(STO_CONN)
        cont = bs.get_container_client(STO_CONT)
        cont.upload_blob(
            name = f"{pid}_results.xlsx",
            data = buf.getvalue(),
            overwrite = True,
            content_settings = ContentSettings(
                content_type=("application/vnd.openxmlformats-officedocument."
                              "spreadsheetml.sheet"))
        )
    except Exception as exc:
        logging.exception("Blob upload error")
        return resp(500, f"Blob error : {exc}")

    return resp(200, "OK")
