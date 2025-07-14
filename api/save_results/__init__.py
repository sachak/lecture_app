import os, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── Variables d’environnement ──────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")                   # Chaîne ODBC
API_SECRET = os.getenv("API_SECRET")                 # header x-api-secret
STO_CONN   = os.getenv("STORAGE_CONN")               # Chaîne connexion Storage
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results")

# ─── Helpers ────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"

def http_resp(code: int, body: str = "") -> func.HttpResponse:
    # on journalise systématiquement le texte pour les erreurs ≥400
    if code >= 400:
        logging.error(body or f"HTTP {code}")
    return func.HttpResponse(
        body, status_code=code,
        headers={
            "Access-Control-Allow-Origin":"*",
            "Access-Control-Allow-Methods":"POST,OPTIONS",
            "Access-Control-Allow-Headers":"Content-Type,x-api-secret"
        })

# ─── Function entry point ───────────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    # CORS pre-flight
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

    # ─── Vérif stricte : nblettres doit exister pour chaque essai test ──
    for i, r in enumerate(data, 1):
        if r.get("phase") != "practice" and r.get("nblettres") in (None, ""):
            return http_resp(400, f"nblettres missing in item {i}")

    # ─── Garder uniquement la phase test ────────────────────────────────
    test_data = [r for r in data if r.get("phase") != "practice"]
    if not test_data:
        return http_resp(200, "OK (practice only)")

    # ─── Insertion SQL ──────────────────────────────────────────────────
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in test_data:
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
                    int(r["nblettres"])
                )
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL insert")
        return http_resp(500, f"DB error : {exc}")

    # ─── DataFrame complet ──────────────────────────────────────────────
    df = pd.DataFrame(test_data)
    df["letters_block"] = df["nblettres"].apply(letters_block)

    # ─── Stats ByGroup ─────────────────────────────────────────────────
    stats_grp = (
        df.groupby("groupe")
          .agg(
              n_sd               = ('rt_ms',     'count'),
              rt_ms_mean         = ('rt_ms',     'mean'),
              rt_ms_sd           = ('rt_ms',     'std'),
              nblettres_mean     = ('nblettres', 'mean'),
              nblettres_sd       = ('nblettres', 'std'),
              nbphons_mean       = ('nbphons',   'mean'),
              nbphons_sd         = ('nbphons',   'std'),
              old20_mean         = ('old20',     'mean'),
              old20_sd           = ('old20',     'std'),
              pld20_mean         = ('pld20',     'mean'),
              pld20_sd           = ('pld20',     'std'),
              freqfilms2_mean    = ('freqfilms2',   'mean'),
              freqfilms2_sd      = ('freqfilms2',   'std'),
              freqlemfilms2_mean = ('freqlemfilms2','mean'),
              freqlemfilms2_sd   = ('freqlemfilms2','std'),
              freqlemlivres_mean = ('freqlemlivres','mean'),
              freqlemlivres_sd   = ('freqlemlivres','std'),
              freqlivres_mean    = ('freqlivres',   'mean'),
              freqlivres_sd      = ('freqlivres',   'std')
          )
          .reset_index()
          .rename(columns={"groupe": "groupe_sd"})
    )

    # ─── Stats ByLetters ───────────────────────────────────────────────
    stats_blk = (
        df.groupby("letters_block")
          .agg(
              n_sd               = ('rt_ms',     'count'),
              rt_ms_mean         = ('rt_ms',     'mean'),
              rt_ms_sd           = ('rt_ms',     'std'),
              nblettres_mean     = ('nblettres', 'mean'),
              nblettres_sd       = ('nblettres', 'std'),
              nbphons_mean       = ('nbphons',   'mean'),
              nbphons_sd         = ('nbphons',   'std'),
              old20_mean         = ('old20',     'mean'),
              old20_sd           = ('old20',     'std'),
              pld20_mean         = ('pld20',     'mean'),
              pld20_sd           = ('pld20',     'std'),
              freqfilms2_mean    = ('freqfilms2',   'mean'),
              freqfilms2_sd      = ('freqfilms2',   'std'),
              freqlemfilms2_mean = ('freqlemfilms2','mean'),
              freqlemfilms2_sd   = ('freqlemfilms2','std'),
              freqlemlivres_mean = ('freqlemlivres','mean'),
              freqlemlivres_sd   = ('freqlemlivres','std'),
              freqlivres_mean    = ('freqlivres',   'mean'),
              freqlivres_sd      = ('freqlivres',   'std')
          )
          .reset_index()
          .rename(columns={"letters_block": "letters_block_sd"})
    )

    # ─── Excel en mémoire ──────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel       (wr, "tirage",          index=False)
        stats_grp.to_excel(wr, "Stats_ByGroup",   index=False)
        stats_blk.to_excel(wr, "Stats_ByLetters", index=False)
    buf.seek(0)

    # ─── Upload Blob ───────────────────────────────────────────────────
    try:
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            name=f"{pid}_results.xlsx",
            data=buf.getvalue(),
            overwrite=True,
            content_settings=ContentSettings(
                content_type=("application/vnd.openxmlformats-officedocument."
                              "spreadsheetml.sheet"))
        )
    except Exception as exc:
        logging.exception("Blob upload")
        return http_resp(500, f"Blob error : {exc}")

    return http_resp(200, "OK")
