# download_all – export Excel complet (hors phase practice)
import os, io, pandas as pd, pyodbc, azure.functions as func

SQL_CONN   = os.getenv("SQL_CONN")
API_SECRET = os.getenv("API_SECRET")

def letters_block(n:int) -> str:
    if n in (4,5):   return "4_5"
    if n in (6,7):   return "6_7"
    if n in (8,9):   return "8_9"
    return "10_11"

# ---------------------------------------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    if req.method == "OPTIONS":
        return _cors(204, "")

    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # ----- lecture SQL (sans practice) -------------------------------------
    with pyodbc.connect(SQL_CONN, timeout=30) as cnx:
        df = pd.read_sql(
            "SELECT * FROM dbo.resultats "
            "WHERE phase <> 'practice' "
            "ORDER BY id", cnx)

    if df.empty:
        return _cors(404, "Table vide")

    df["letters_block"] = df["nblettres"].apply(letters_block)

    # ---------------- stats par participant × groupe -----------------------
    part_grp = (df.groupby(["participant","groupe"])["rt_ms"]
                  .agg(['count','mean','std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    # ---------------- stats par participant × bloc lettres -----------------
    part_blk = (df.groupby(["participant","letters_block"])["rt_ms"]
                  .agg(['count','mean','std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))

    # ---------------- stats globales ---------------------------------------
    glob_grp = (df.groupby("groupe")["rt_ms"]
                  .agg(['count','mean','std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))
    glob_grp.insert(0,"participant","ALL")

    glob_blk = (df.groupby("letters_block")["rt_ms"]
                  .agg(['count','mean','std']).reset_index()
                  .rename(columns={'count':'n','mean':'rt_mean','std':'rt_sd'}))
    glob_blk.insert(0,"participant","ALL")

    # ---------------- Excel en mémoire -------------------------------------
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df       .to_excel(wr, sheet_name="raw",                 index=False)
        part_grp .to_excel(wr, sheet_name="Stats_Part_Group",    index=False)
        part_blk .to_excel(wr, sheet_name="Stats_Part_Letters",  index=False)
        glob_grp .to_excel(wr, sheet_name="Stats_Global_Group",  index=False)
        glob_blk .to_excel(wr, sheet_name="Stats_Global_Letters",index=False)
    buf.seek(0)

    return func.HttpResponse(
        buf.read(),
        status_code=200,
        mimetype=("application/vnd.openxmlformats-officedocument."
                  "spreadsheetml.sheet"),
        headers={
          "Content-Disposition":"attachment; filename=all_results.xlsx",
          "Access-Control-Allow-Origin":"*"
        })

# ---------------------------------------------------------------------------
def _cors(code:int, body:str) -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
          "Access-Control-Allow-Origin":"*",
          "Access-Control-Allow-Methods":"GET,OPTIONS",
          "Access-Control-Allow-Headers":"x-api-secret"
        })
