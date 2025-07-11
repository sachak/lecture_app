# save_results.py  — adapté Python 3.9  (pas d’opérateur “|”)
import os, json, logging, traceback, azure.functions as func

try:
    import pyodbc
    PYODBC_ERR = None
except Exception as e:
    pyodbc, PYODBC_ERR = None, e

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

SQL_CONN   = os.getenv("SQL_CONN")
API_SECRET = os.getenv("API_SECRET")

@app.route(route="save_results", methods=["POST", "OPTIONS"],
           auth_level=func.AuthLevel.FUNCTION)
def save_results(req: func.HttpRequest) -> func.HttpResponse:
    debug = req.params.get("debug", "0").lower() in ("1", "true")

    if req.method == "OPTIONS":
        return _cors(204, "")

    if PYODBC_ERR:
        return _problem(500, f"Import pyodbc failed : {PYODBC_ERR}",
                        debug, True)

    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _problem(403, "Wrong or missing x-api-secret header", debug)

    if not SQL_CONN:
        return _problem(500, "Environment variable SQL_CONN missing",
                        debug)

    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return _problem(400, f"Invalid JSON : {exc}",
                        debug, True)

    try:
        with pyodbc.connect(SQL_CONN, timeout=5) as cnx, cnx.cursor() as cur:
            for row in data:
                _check(row)
                cur.execute("""INSERT INTO resultats
                               (word, rt_ms, response, phase)
                               VALUES (?,?,?,?)""",
                            row["word"], int(row["rt_ms"]),
                            row["response"], row["phase"])
            cnx.commit()
        return _cors(200, "OK")
    except Exception as exc:
        logging.exception("SQL error")
        return _problem(500, f"DB error : {exc}", debug, True)

# ---------- utilitaires ------------------------------------------------------
from typing import Optional
def _cors(code: int, body: str = "") -> func.HttpResponse:
    return func.HttpResponse(
        body, status_code=code,
        headers={"Access-Control-Allow-Origin":"*",
                 "Access-Control-Allow-Methods":"POST,OPTIONS",
                 "Access-Control-Allow-Headers":"Content-Type,x-api-secret"})

def _problem(code: int, msg: str, dbg: bool,
             add_trace: bool = False) -> func.HttpResponse:
    import json
    body = {"status": code, "error": msg}
    if add_trace:
        body["traceback"] = traceback.format_exc()
    http_code = 200 if dbg else code
    return func.HttpResponse(json.dumps(body, indent=2, ensure_ascii=False),
                             status_code=http_code,
                             mimetype="application/json",
                             headers={"Access-Control-Allow-Origin":"*"})

def _check(r: dict):
    need = ["word","rt_ms","response","phase"]
    miss = [k for k in need if k not in r]
    if miss:
        raise ValueError("Missing keys: " + ", ".join(miss))
