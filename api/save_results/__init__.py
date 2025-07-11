import os, io, json, logging, traceback
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── variables d’environnement ──────────────────────────────────────────
SQL_CONN    = os.getenv("SQL_CONN")                     # chaîne ODBC
API_SECRET  = os.getenv("API_SECRET")                   # header facultatif
STO_CONN    = os.getenv("STORAGE_CONN")                 # chaîne Storage
STO_CONT    = os.getenv("STORAGE_CONTAINER", "results") # conteneur Blob

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

def build_stats(df: pd.DataFrame, by_cols: list[str]) -> pd.DataFrame:
    numeric_cols = [c for c in df.select_dtypes(include="number").columns
                    if c not in by_cols]
    agg = {"n": ("rt_ms", "count")}
    for col in numeric_cols:
        agg[f"{col}_mean"] = (col, "mean")
        agg[f"{col}_sd"]   = (col, "std")
    stat = df.groupby(by_cols).agg(**agg).reset_index()
    return stat

# ─── Function entry point (v1) ──────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    debug_mode = req.params.get("debug", "").lower() in ("1", "true")

    try:
        # ── CORS pré-vol ---------------------------------------------------
        if req.method == "OPTIONS":
            return http_resp(204)

        # ── Secret X-API --------------------------------------------------
        if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
            return http_resp(403, "Forbidden")

        # ── Lecture JSON --------------------------------------------------
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
        if not data or "participant" not in data[0]:
            raise ValueError("participant missing")

        pid = str(data[0]["participant"]).strip() or "anon"

        # ── Insertion SQL -------------------------------------------------
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

        # ── DataFrame hors practice --------------------------------------
        df = pd.DataFrame(data)
        df = df[df.phase != "practice"].copy()
        if df.empty:
            return http_resp(200, "OK (practice only)")

        df["letters_block"] = df["nblettres"].apply(letters_block)

        stats_grp = build_stats(df, ["groupe"])
        stats_blk = build_stats(df, ["letters_block"])

        # ── Excel en mémoire ---------------------------------------------
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as wr:
            df.to_excel      (wr, "tirage",          index=False)
            stats_grp.to_excel(wr,"Stats_ByGroup",   index=False)
            stats_blk.to_excel(wr,"Stats_ByLetters", index=False)
        buf.seek(0)

        # ── Upload Blob ---------------------------------------------------
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            f"{pid}_results.xlsx",
            buf.getvalue(),
            overwrite=True,
            content_settings=ContentSettings(
              content_type="application/vnd.openxmlformats-officedocument."
                           "spreadsheetml.sheet")
        )

        return http_resp(200, "OK")

    # ── Gestion des exceptions globales ----------------------------------
    except Exception as exc:
        logging.exception("save_results failed")

        if debug_mode:
            body = json.dumps({
                "status"   : 500,
                "error"    : str(exc),
                "traceback": traceback.format_exc()
            }, indent=2)
            return func.HttpResponse(
                body,
                status_code=200,                # 200 pour afficher le body
                mimetype="application/json",
                headers={"Access-Control-Allow-Origin":"*"}
            )
        return http_resp(500)
