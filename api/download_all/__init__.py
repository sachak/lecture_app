# download_all  –  Azure Static Web App (Functions v1)
# ---------------------------------------------------
# Renvoie un fichier all_results.xlsx contenant :
#   • raw                : toutes les réponses (phase <> 'practice')
#   • Stats_ByGroup      : stats RT par participant × groupe
#   • Stats_ByLetters    : stats RT par participant × bloc de longueur

import os, io
import pandas as pd
import pyodbc
import azure.functions as func

# ---------- configuration ---------------------------------------------------
SQL_CONN   = os.getenv("SQL_CONN")          # chaîne ODBC vers Azure SQL
API_SECRET = os.getenv("API_SECRET")        # même secret que save_results

# ---------- bloc longueur ---------------------------------------------------
def letters_block(n: int) -> str:
    if n in (4, 5):
        return "4_5"
    if n in (6, 7):
        return "6_7"
    if n in (8, 9):
        return "8_9"
    return "10_11"                          # 10 ou 11 lettres

# ---------- helper CORS -----------------------------------------------------
def _cors(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
            "Access-Control-Allow-Origin" : "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "x-api-secret"
        })

# ---------- MAIN ------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    # Pré-vol CORS
    if req.method == "OPTIONS":
        return _cors(204)

    # Vérification du secret
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # ------------------------------------------------------------------ SQL
    with pyodbc.connect(SQL_CONN, timeout=30) as cnx:
        df = pd.read_sql(
            """
            SELECT id, word, rt_ms, response, phase,
                   participant, groupe, nblettres, created_at
            FROM   dbo.resultats
            WHERE  phase <> 'practice'         -- on exclut l'entraînement
            ORDER  BY id
            """,
            cnx
        )

    if df.empty:
        return _cors(404, "Aucune donnée (table vide)")

    # Ajout du bloc de longueur
    df["letters_block"] = df["nblettres"].apply(letters_block)

    # ---------------------------------------------------------------- Stats
    # 1. Stats par participant × groupe
    part_grp = (df.groupby(["participant", "groupe"])["rt_ms"]
                  .agg(['count', 'mean', 'std'])
                  .reset_index()
                  .rename(columns={'count': 'n',
                                   'mean' : 'rt_mean',
                                   'std'  : 'rt_sd'}))

    # 2. Stats par participant × bloc lettres
    part_blk = (df.groupby(["participant", "letters_block"])["rt_ms"]
                  .agg(['count', 'mean', 'std'])
                  .reset_index()
                  .rename(columns={'count': 'n',
                                   'mean' : 'rt_mean',
                                   'std'  : 'rt_sd'}))

    # ---------------------------------------------------------------- Excel
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel      (wr, sheet_name="raw",             index=False)
        part_grp.to_excel(wr, sheet_name="Stats_ByGroup",   index=False)
        part_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)
    buf.seek(0)

    return func.HttpResponse(
        buf.read(),
        status_code = 200,
        mimetype = ("application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"),
        headers = {
            "Content-Disposition": "attachment; filename=all_results.xlsx",
            "Access-Control-Allow-Origin": "*"
        })
