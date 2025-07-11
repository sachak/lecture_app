import os, json, io, logging
import pandas as pd
import pyodbc, azure.functions as func
from azure.storage.blob import BlobServiceClient

# ---------- paramètres ------------------------------------------------------
SQL_CONN     = os.getenv("SQL_CONN")
API_SECRET   = os.getenv("API_SECRET")          # facultatif
STO_CONN     = os.getenv("STORAGE_CONN")
STO_CONT     = os.getenv("STORAGE_CONTAINER", "sascharesults")

# ---------- utils -----------------------------------------------------------
def letters_block(n:int)->str:
    if n in (4,5):   return "4_5"
    if n in (6,7):   return "6_7"
    if n in (8,9):   return "8_9"
    return "10_11"

def cors(code:int, body:str=""):
    return func.HttpResponse(
        body, status_code=code,
        headers={
          "Access-Control-Allow-Origin":"*",
          "Access-Control-Allow-Methods":"POST,OPTIONS",
          "Access-Control-Allow-Headers":"Content-Type,x-api-secret"})

# ---------- main ------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    if req.method=="OPTIONS":
        return cors(204)

    if API_SECRET and req.headers.get("x-api-secret")!=API_SECRET:
        return cors(403,"Forbidden")

    try:
        data = req.get_json()
        if not isinstance(data,list): raise ValueError("JSON must be a list")
    except Exception as e:
        return cors(400,f"Invalid JSON : {e}")

    # obligatoire : participant et groupe & nblettres dans chaque essai
    if not data or "participant" not in data[0]:
        return cors(400,"participant missing")

    pid = data[0]["participant"]

    # ------------------ insertion SQL ---------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute(
                  """INSERT INTO dbo.resultats
                     (word,rt_ms,response,phase,participant,groupe,nblettres)
                     VALUES (?,?,?,?,?,?,?)""",
                  r.get("word",""),
                  int(r.get("rt_ms",0)),
                  r.get("response",""),
                  r.get("phase",""),
                  r.get("participant",""),
                  r.get("groupe",""),
                  r.get("nblettres"))
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL error")
        return cors(500,f"DB error : {exc}")

    # ------------------ construction Excel ----------------------------------
    df = pd.DataFrame(data)
    df = df[df.phase!="practice"].copy()
    if df.empty:
        return cors(200,"OK (practice only)")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    stats_grp = (df.groupby(["groupe"])["rt_ms"]
                   .agg(['count','mean','std'])
                   .reset_index()
                   .rename(columns={'count':'n',
                                    'mean':'rt_mean','std':'rt_sd'}))

    stats_blk = (df.groupby(["letters_block"])["rt_ms"]
                   .agg(['count','mean','std'])
                   .reset_index()
                   .rename(columns={'count':'n',
                                    'mean':'rt_mean','std':'rt_sd'}))

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel       (wr, sheet_name="raw",             index=False)
        stats_grp.to_excel(wr, sheet_name="Stats_ByGroup",   index=False)
        stats_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)
    buf.seek(0)

    # ------------------ upload dans Blob -------------------------------------
    try:
        blob = BlobServiceClient.from_connection_string(STO_CONN)
        container = blob.get_container_client(STO_CONT)
        container.upload_blob(name=f"{pid}_results.xlsx",
                              data=buf.getvalue(),
                              overwrite=True)
    except Exception as exc:
        logging.exception("Blob upload error")
        return cors(500,f"Blob error : {exc}")

    return cors(200,"OK")
