# -*- coding: utf-8 -*-
# =============================================================
# Azure Function  (Python v1)  –  enregistrement + export XLSX
# =============================================================
import os, io, logging
import pandas as pd
import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

# ──────────────────────────────────────────────────────────────
# Variables d’environnement
# ──────────────────────────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")                     # chaîne ODBC
API_SECRET = os.getenv("API_SECRET")                   # header x-api-secret
STO_CONN   = os.getenv("STORAGE_CONN")                 # Azure Storage
STO_CONT   = os.getenv("STORAGE_CONTAINER", "results") # conteneur blobs

# ──────────────────────────────────────────────────────────────
# Helpers généraux
# ──────────────────────────────────────────────────────────────
def letters_block(n: int) -> str:
    """Catégorise la longueur en lettres comme dans le générateur de stimuli."""
    if n in (4, 5):  return "4_5"
    if n in (6, 7):  return "6_7"
    if n in (8, 9):  return "8_9"
    return "10_11"

def http_resp(code: int, body: str = "") -> func.HttpResponse:
    """Réponse HTTP avec en-têtes CORS."""
    return func.HttpResponse(
        body,
        status_code=code,
        headers={
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        }
    )

# ──────────────────────────────────────────────────────────────
# Fonctions de statistiques (copiées du générateur de stimuli)
# ──────────────────────────────────────────────────────────────
def _numeric_cols(dframe: pd.DataFrame) -> list[str]:
    """Colonnes numériques à résumer (on exclut les colonnes méta)."""
    meta = {"word", "response", "phase", "participant",
            "groupe", "letters_block"}
    return [c for c in dframe.columns
            if c not in meta and pd.api.types.is_numeric_dtype(dframe[c])]

def stats_by_group_and_block(dframe: pd.DataFrame) -> pd.DataFrame:
    """Stats par bloc de lettres ET par groupe."""
    num = _numeric_cols(dframe)
    rows = []
    for blk in ("4_5", "6_7", "8_9", "10_11"):
        mask_blk = dframe.letters_block == blk
        for grp in sorted(dframe.groupe.unique()):
            sub = dframe[mask_blk & (dframe.groupe == grp)]
            if sub.empty:
                continue
            rec = {"letters_block": blk, "group": grp, "n": len(sub)}
            for c in num:
                rec[f"{c}_mean"] = sub[c].mean()
                rec[f"{c}_sd"]   = sub[c].std(ddof=0)
            rows.append(rec)
    return pd.DataFrame(rows)

def stats_by_block_total(dframe: pd.DataFrame) -> pd.DataFrame:
    """Stats par bloc de lettres (tous groupes confondus)."""
    num = _numeric_cols(dframe)
    rows = []
    for blk in ("4_5", "6_7", "8_9", "10_11"):
        sub = dframe[dframe.letters_block == blk]
        rec = {"letters_block": blk, "n": len(sub)}
        for c in num:
            rec[f"{c}_mean"] = sub[c].mean()
            rec[f"{c}_sd"]   = sub[c].std(ddof=0)
        rows.append(rec)
    return pd.DataFrame(rows)

# ──────────────────────────────────────────────────────────────
# Point d’entrée (Python v1 : def main(req) -> HttpResponse)
# ──────────────────────────────────────────────────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:

    # Pré-vol CORS --------------------------------------------------
    if req.method == "OPTIONS":
        return http_resp(204)

    # Vérification du secret ---------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return http_resp(403, "Forbidden")

    # Lecture / validation du JSON ---------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return http_resp(400, f"Invalid JSON : {exc}")

    if not data or "participant" not in data[0]:
        return http_resp(400, "participant missing")

    pid = str(data[0].get("participant", "")).strip() or "anon"

    # ──────────────────────────────────────────────────────────────
    # Insertion SQL
    # ──────────────────────────────────────────────────────────────
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

    # ──────────────────────────────────────────────────────────────
    # Construction des DataFrames pour l’export
    # ──────────────────────────────────────────────────────────────
    df = pd.DataFrame(data)
    df = df[df.phase != "practice"].copy()          # on ignore la pratique
    if df.empty:
        return http_resp(200, "OK (practice only)")

    # Ajout du bloc de lettres
    df["letters_block"] = df["nblettres"].apply(letters_block)

    # Statistiques identiques au générateur de stimuli
    stats_grp = stats_by_group_and_block(df)
    stats_blk = stats_by_block_total(df)

    # ──────────────────────────────────────────────────────────────
    # Création du classeur Excel en mémoire
    # ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel      (wr, sheet_name="tirage",          index=False)  # feuille brute
        stats_grp.to_excel(wr, sheet_name="Stats_ByGroup",   index=False)
        stats_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)
    buf.seek(0)

    # ──────────────────────────────────────────────────────────────
    # Upload du fichier dans Azure Blob Storage
    # ──────────────────────────────────────────────────────────────
    try:
        bs  = BlobServiceClient.from_connection_string(STO_CONN)
        cnt = bs.get_container_client(STO_CONT)
        cnt.upload_blob(
            name       = f"{pid}_results.xlsx",
            data       = buf.getvalue(),
            overwrite  = True,
            content_settings = ContentSettings(
                content_type=("application/vnd.openxmlformats-officedocument."
                              "spreadsheetml.sheet")
            )
        )
    except Exception as exc:
        logging.exception("Blob upload")
        return http_resp(500, f"Blob error : {exc}")

    # ──────────────────────────────────────────────────────────────
    return http_resp(200, "OK")
