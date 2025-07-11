# api/save_results/__init__.py   – compatible modèle v1 + Python 3.9
import os, json, logging, traceback
import azure.functions as func

# ─── tentative d'import de pyodbc ────────────────────────────────────────────
try:
    import pyodbc
    PYODBC_ERR = None
except Exception as e:
    pyodbc, PYODBC_ERR = None, e          # on mémorise l’erreur

# ─── variables d’environnement ───────────────────────────────────────────────
SQL_CONN   = os.getenv("SQL_CONN")         # obligatoire
API_SECRET = os.getenv("API_SECRET")       # facultatif

# ─── point d’entrée v1 :  def main(req: func.HttpRequest) ───────────────────
def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/save_results
    OPTIONS pour CORS
    Ajoutez ?debug=1 pour forcer le statut HTTP à 200 et voir le corps.
    """
    debug = req.params.get("debug", "0").lower() in ("1", "true")

    if req.method == "OPTIONS":                       # pré-vol CORS
        return _cors(204, "")

    # 1) pyodbc absent → on l'indique clairement
    if PYODBC_ERR:
        return _problem(500, f"Import pyodbc failed : {PYODBC_ERR}",
                        debug, trace=True)

    # 2) secret incorrect
    if API_SECRET and req.headers.get("x-api-secret") != API_SECRET:
        return _problem(403, "Wrong or missing x-api-secret header", debug)

    # 3) chaîne SQL manquante
    if not SQL_CONN:
        return _problem(500, "Environment variable SQL_CONN missing", debug)

    # 4) JSON
    try:
        data = req.get_json()
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")
    except Exception as exc:
        return _problem(400, f"Invalid JSON : {exc}", debug, trace=True)

    # 5) insertion SQL
    try:
        with pyodbc.connect(SQL_CONN, timeout=5) as cnx, cnx.cursor() as cur:
            for row in data:
                _check(row)
                cur.execute(
                    "INSERT INTO resultats (word, rt_ms, response, phase) "
                    "VALUES (?,?,?,?)",
                    row["word"], int(row["rt_ms"]),
                    row["response"], row["phase"])
            cnx.commit()
        return _cors(200, "OK")

    except Exception as exc:
        logging.exception("SQL error")
        return _problem(500, f"DB error : {exc}", debug, trace=True)

# ─── petites fonctions utilitaires ───────────────────────────────────────────
def _check(r):
    need = ["word", "rt_ms", "response", "phase"]
    miss = [k for k in need if k not in r]
    if miss:
        raise ValueError("Missing keys: " + ", ".join(miss))

def _cors(code, body=""):
    return func.HttpResponse(
        body, status_code=code,
        headers={"Access-Control-Allow-Origin":"*",
                 "Access-Control-Allow-Methods":"POST,OPTIONS",
                 "Access-Control-Allow-Headers":"Content-Type,x-api-secret"})

def _problem(code, msg, dbg, trace=False):
    body = {"status": code, "error": msg}
    if trace:
        body["traceback"] = traceback.format_exc()
    http_code = 200 if dbg else code
    return func.HttpResponse(
        json.dumps(body, indent=2, ensure_ascii=False),
        status_code=http_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin":"*"})
