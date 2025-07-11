# -*- coding: utf-8 -*-
# =============================================================
# Azure Function  save_results  (Python v1)
# =============================================================
import os, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings


# ──────────────────────────────────────────────────────────────
# Variables d’environnement
# ──────────────────────────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")                       # chaîne ODBC
API_SECRET = os.getenv("API_SECRET")                     # clé secrète HTTP
STO_CONN   = os.getenv("STORAGE_CONN")                   # chaîne Azure Storage
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results")   # conteneur blobs


# ──────────────────────────────────────────────────────────────
# Helpers généraux
# ──────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"


def http_resp(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        })


# ──────────────────────────────────────────────────────────────
# Fonctions de statistiques  (identiques au générateur stimuli)
# ──────────────────────────────────────────────────────────────
META_COLS = {
    "word", "response", "phase", "participant",
    "groupe", "letters_block"
}

def _numeric_cols(df: pd.DataFrame) -> list[str]:
    """Toutes les colonnes numériques qui ne sont pas ‘méta’."""
    return [
        c for c in df.columns
        if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]


def stats_by_group_and_block(df: pd.DataFrame) -> pd.DataFrame:
    """Moyennes & écarts-types par bloc de lettres ET par groupe."""
    nums, rows = _numeric_cols(df), []
    for blk in ("4_5", "6_7", "8_9", "10_11"):
        m_blk = df.letters_block == blk
        for grp in sorted(df.groupe.unique()):
            sub = df[m_blk & (df.groupe == grp)]
            if sub.empty:
                continue
            rec = {"letters_block": blk, "group": grp, "n": len(sub)}
            for c in nums:
                rec[f"{c}_mean"] = sub[c].mean()
                rec[f"{c}_sd"]   = sub[c].std(ddof=0)
            rows.append(rec)
    return pd.DataFrame(rows)


def stats_by_block_total(df: pd.DataFrame) -> pd.DataFrame:
    """Moyennes & écarts-types par bloc de lettres (tous groupes confondus)."""
    nums, rows = _numeric_cols(df), []
    for blk in ("4_5", "6_7", "8_9", "10_11"):
        sub = df[df.letters_block == blk]
        rec = {"letters_block": blk, "n": len(sub)}
        for c in nums:
            rec[f"{c}_mean"] = sub[c].mean()
            rec[f"{c}_sd"]   = sub[c].std(ddof=0)
        rows.append(rec)
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────
# Point d’entrée Function
# ──────────────────────────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    # ---------- CORS pre-flight ----------
    if req.method == "OPTIONS":
        return http_resp(204)

    # ---------- Secret ----------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return http_resp(403, "Forbidden")

    # ---------- Lecture JSON ----------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return http_resp(400, f"Invalid JSON : {exc}")

    if not data or "participant" not in data[0]:
        return http_resp(400, "participant missing")

    pid = str(data[0]["participant"]).strip() or "anon"

    # ──────────────────────────────────────────────────────────
    # Insertion SQL
    # ──────────────────────────────────────────────────────────
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
                    r.get("word",      ""),
                    int(r.get("rt_ms", 0)),
                    r.get("response",  ""),
                    r.get("phase",     ""),
                    r.get("participant",""),
                    r.get("groupe",    ""),
                    r.get("nblettres")
                )
            cnx.commit()
    except Exception as exc:
        logging.exception("SQL insert")
        return http_resp(500, f"DB error : {exc}")

    # ──────────────────────────────────────────────────────────
    # DataFrame + stats
    # ──────────────────────────────────────────────────────────
    try:
        df = pd.DataFrame(data)
        df = df[df.phase != "practice"].copy()
        if df.empty:
            return http_resp(200, "OK (practice only)")

        df["letters_block"] = df["nblettres"].apply(letters_block)
        stats_grp = stats_by_group_and_block(df)
        stats_blk = stats_by_block_total(df)
    except Exception as exc:
        logging.exception("DataFrame/stats")
        return http_resp(500, f"Pandas error : {exc}")

    # ──────────────────────────────────────────────────────────
    # Création du classeur Excel en mémoire
    # ──────────────────────────────────────────────────────────
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as wr:
            df.to_excel      (wr, "tirage",          index=False)
            stats_grp.to_excel(wr, "Stats_ByGroup",   index=False)
            stats_blk.to_excel(wr, "Stats_ByLetters", index=False)
        buf.seek(0)
    except Exception as exc:
        logging.exception("Excel build")
        return http_resp(500, f"Excel error : {exc}")

    # ──────────────────────────────────────────────────────────
    # Upload Blob Storage
    # ──────────────────────────────────────────────────────────
    try:
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            name=f"{pid}_results.xlsx",
            data=buf.getvalue(),
            overwrite=True,
            content_settings=ContentSettings(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        )
    except Exception as exc:
        logging.exception("Blob upload")
        return http_resp(500, f"Blob error : {exc}")

    return http_resp(200, "OK")
