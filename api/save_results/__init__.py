# -*- coding: utf-8 -*-
# =============================================================
# Azure Function  save_results  (Python v1)
# =============================================================
import os, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ─── variables d’environnement ───────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")
API_SECRET = os.getenv("API_SECRET")
STO_CONN   = os.getenv("STORAGE_CONN")
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results")

# ─── helpers ─────────────────────────────────────────────────
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

# ─── listes de colonnes méta (non numériques) ────────────────
META = {"word","response","phase","participant","groupe","letters_block"}

def numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns
            if c not in META and pd.api.types.is_numeric_dtype(df[c])]

# ─── point d’entrée ──────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    if req.method == "OPTIONS":
        return http_resp(204)

    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return http_resp(403, "Forbidden")

    # -------- JSON -------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return http_resp(400, f"Invalid JSON : {exc}")

    if not data or "participant" not in data[0]:
        return http_resp(400, "participant missing")

    pid = str(data[0]["participant"]).strip() or "anon"

    # -------- INSERT SQL ------------------------------------------
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute("""
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

    # -------- DataFrame hors practice ----------------------------
    df = pd.DataFrame(data)
    df = df[df.phase != "practice"].copy()
    if df.empty:
        return http_resp(200, "OK (practice only)")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    # -------- calcul statistiques (nouveau) -----------------------
    try:
        nums = numeric_cols(df)

        # ByGroup + Block
        rows_grp = []
        for blk in ("4_5","6_7","8_9","10_11"):
            m_blk = df.letters_block == blk
            for grp in sorted(df.groupe.unique()):
                sub = df[m_blk & (df.groupe == grp)]
                if sub.empty: continue
                rec = {"letters_block": blk, "group": grp, "n": len(sub)}
                for c in nums:
                    rec[f"{c}_mean"] = sub[c].mean()
                    rec[f"{c}_sd"]   = sub[c].std(ddof=0)
                rows_grp.append(rec)
        stats_grp = pd.DataFrame(rows_grp)

        # ByLetters (tous groupes)
        rows_blk = []
        for blk in ("4_5","6_7","8_9","10_11"):
            sub = df[df.letters_block == blk]
            rec = {"letters_block": blk, "n": len(sub)}
            for c in nums:
                rec[f"{c}_mean"] = sub[c].mean()
                rec[f"{c}_sd"]   = sub[c].std(ddof=0)
            rows_blk.append(rec)
        stats_blk = pd.DataFrame(rows_blk)

    except Exception as exc:
        logging.exception("Stats build")
        return http_resp(500, f"Stats error : {exc}")

    # -------- Excel en mémoire ------------------------------------
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

    # -------- Upload Blob -----------------------------------------
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
