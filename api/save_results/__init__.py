import os, io, json, logging, traceback
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── variables d’environnement ──────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")
API_SECRET = os.getenv("API_SECRET")
STO_CONN   = os.getenv("STORAGE_CONN")
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results")

# ─── helpers ────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"

def cors_headers():
    return {
      "Access-Control-Allow-Origin":"*",
      "Access-Control-Allow-Methods":"POST,OPTIONS",
      "Access-Control-Allow-Headers":"Content-Type,x-api-secret"
    }

def http_resp(code:int, body:str=""):
    return func.HttpResponse(body, status_code=code, headers=cors_headers())

# ---------- statistiques complètes -------------------------------------
def build_stats(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    # on retire rt_ms pour ne pas le dupliquer (déjà utilisé pour le compteur n)
    numeric = [c for c in df.select_dtypes(include="number").columns
               if c not in by and c != "rt_ms"]
    agg = {"n": ("rt_ms", "count")}
    for col in numeric:
        agg[f"{col}_mean"] = (col, "mean")
        agg[f"{col}_sd"]   = (col, "std")
    return df.groupby(by).agg(**agg).reset_index()

# ─── Function entry point (v1) ──────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:
    debug = req.params.get("debug","").lower() in ("1","true")

    try:
        # CORS pré-vol
        if req.method == "OPTIONS":
            return http_resp(204)

        # secret
        if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
            return http_resp(403,"Forbidden")

        # JSON
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be list")
        if not data or "participant" not in data[0]:
            raise ValueError("participant missing")
        pid = str(data[0]["participant"]).strip() or "anon"

        # insert SQL
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute("""
                  INSERT INTO dbo.resultats
                    (word, rt_ms, response, phase,
                     participant, groupe, nblettres)
                  VALUES (?,?,?,?,?,?,?)""",
                  r.get("word",""),
                  int(r.get("rt_ms",0)),
                  r.get("response",""),
                  r.get("phase",""),
                  r.get("participant",""),
                  r.get("groupe",""),
                  r.get("nblettres"))
            cnx.commit()

        # dataframe hors practice
        df = pd.DataFrame(data)
        df = df[df.phase!="practice"].copy()
        if df.empty:
            return http_resp(200,"OK (practice only)")

        df["letters_block"] = df["nblettres"].apply(letters_block)

        stats_grp = build_stats(df, ["groupe"])
        stats_blk = build_stats(df, ["letters_block"])

        # Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as wr:
            df.to_excel      (wr,"tirage",          index=False)
            stats_grp.to_excel(wr,"Stats_ByGroup",   index=False)
            stats_blk.to_excel(wr,"Stats_ByLetters", index=False)
        buf.seek(0)

        # upload Blob
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            f"{pid}_results.xlsx", buf.getvalue(), overwrite=True,
            content_settings=ContentSettings(
              content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))

        return http_resp(200,"OK")

    except Exception as exc:
        logging.exception("save_results failed")
        if debug:
            body=json.dumps({"status":500,"error":str(exc),
                             "traceback":traceback.format_exc()}, indent=2)
            return func.HttpResponse(body,status_code=200,
                   mimetype="application/json",headers=cors_headers())
        return http_resp(500)
