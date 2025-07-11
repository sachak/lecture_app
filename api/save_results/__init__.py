# save_results – model v1
import os, json, logging, pyodbc, azure.functions as func

SQL_CONN   = os.getenv("SQL_CONN")        # ⇦ chaîne ODBC
API_SECRET = os.getenv("API_SECRET")      # ⇦ header facultatif

def main(req: func.HttpRequest) -> func.HttpResponse:

    # ----- OPTIONS (CORS) ---------------------------------------------------
    if req.method == "OPTIONS":
        return _cors(204, "")

    # ----- Secret -----------------------------------------------------------
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _cors(403, "Forbidden")

    # ----- JSON -------------------------------------------------------------
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        logging.error("Invalid JSON", exc_info=True)
        return _cors(400, f"Invalid JSON : {exc}")

    # ----- INSERT -----------------------------------------------------------
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
                    r.get("word", ""),
                    int(r.get("rt_ms", 0)),
                    r.get("response", ""),
                    r.get("phase", ""),
                    r.get("participant", ""),
                    r.get("groupe", ""),
                    r.get("nblettres")
                )
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("SQL error")
        return func.HttpResponse(
            json.dumps({"status":500, "error":f"DB error : {exc}"},
                       indent=2),
            status_code=500,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin":"*"}
        )

# ---------------------------------------------------------------------------
def _cors(code:int, body:str) -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={
          "Access-Control-Allow-Origin":"*",
          "Access-Control-Allow-Methods":"POST,OPTIONS",
          "Access-Control-Allow-Headers":"Content-Type,x-api-secret"
        })
