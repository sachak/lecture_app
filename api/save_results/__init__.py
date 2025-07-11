# ======================================================================
# save_results  –  Function v1 (Static Web App)
# Insère : word | rt_ms | response | phase | participant
# ======================================================================

import os, json, logging, pyodbc, azure.functions as func

SQL_CONN   = os.getenv("SQL_CONN")        # chaîne ODBC vers Azure SQL
API_SECRET = os.getenv("API_SECRET")      # facultatif : header x-api-secret

# ---------- petite fonction CORS --------------------------------------
def _cors(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
          "Access-Control-Allow-Origin" : "*",
          "Access-Control-Allow-Methods": "POST,OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type,x-api-secret"
        })

# ---------- point d’entrée -------------------------------------------
def main(req: func.HttpRequest) -> func.HttpResponse:

    # Pré-vol
    if req.method == "OPTIONS":
        return _cors(204)

    # Secret
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # Lecture JSON
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        logging.error("Invalid JSON", exc_info=True)
        return _cors(400, f"Invalid JSON : {exc}")

    # Insertion SQL
    try:
        with pyodbc.connect(SQL_CONN, timeout=10) as cnx, cnx.cursor() as cur:
            for r in data:
                cur.execute(
                    """
                    INSERT INTO dbo.resultats
                      (word, rt_ms, response, phase, participant)
                    VALUES (?,?,?,?,?)
                    """,
                    r.get("word",        ""),
                    int(r.get("rt_ms", 0)),
                    r.get("response",    ""),
                    r.get("phase",       ""),
                    r.get("participant", "")
                )
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("SQL error")
        err = json.dumps({"status": 500, "error": f"DB error : {exc}"}, indent=2)
        return func.HttpResponse(
            err,
            status_code=500,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
