#!/usr/bin/env python3
"""CPS Attack Monitor — servidor web.

Uso:
    python app.py --script ../deploy_supervisado.py --pkl modelos/supervisado.pkl
    python app.py --script ../deploy_supervisado.py --pkl modelos/supervisado.pkl --csv data/datas.csv

Abre http://localhost:5000 en el navegador.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from threading import Lock

from flask import Flask, Response, jsonify, render_template, request

from inferencia import ejecutar_inferencia

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))


# ---------------------------------------------------------------- state ----

class ReplayState:
    """Estado del replay: resultados pre-computados + cursor de reproducción."""

    def __init__(self, resultados: list[dict], model_info: dict):
        self.resultados = resultados
        self.total = len(resultados)
        self.model_info = model_info
        self.cursor = 0
        self.paused = False
        self.speed = 1.0
        self.lock = Lock()

    def get(self, idx: int) -> dict:
        return self.resultados[idx]

    def reset(self):
        with self.lock:
            self.cursor = 0

    def set_speed(self, speed: float):
        with self.lock:
            self.speed = max(0.1, min(speed, 100.0))

    def toggle_pause(self) -> bool:
        with self.lock:
            self.paused = not self.paused
            return self.paused


state: ReplayState | None = None


# ---------------------------------------------------------------- routes ----

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info")
def info():
    return jsonify({
        "total_rows": state.total,
        "model": state.model_info,
        "columns": list(state.resultados[0].keys()) if state.resultados else [],
    })


@app.route("/api/control", methods=["POST"])
def control():
    data = request.json or {}
    action = data.get("action")
    if action == "pause":
        paused = state.toggle_pause()
        return jsonify({"paused": paused})
    elif action == "reset":
        state.reset()
        return jsonify({"cursor": 0})
    elif action == "speed":
        s = float(data.get("value", 1))
        state.set_speed(s)
        return jsonify({"speed": state.speed})
    return jsonify({"error": "unknown action"}), 400


@app.route("/stream")
def stream():
    def generate():
        while True:
            if state.paused:
                time.sleep(0.1)
                continue

            with state.lock:
                idx = state.cursor
                speed = state.speed

            if idx >= state.total:
                yield f"event: done\ndata: {json.dumps({'total': state.total})}\n\n"
                break

            evt = state.get(idx)
            yield f"data: {json.dumps(evt)}\n\n"

            with state.lock:
                state.cursor += 1

            time.sleep(1.0 / speed)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ----------------------------------------------------------------- main ----

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True, help="Path al .py de deploy (ej: ../deploy_supervisado.py)")
    ap.add_argument("--pkl", required=True, help="Path al .pkl del modelo")
    ap.add_argument("--csv", default="data/datas.csv", help="Path al CSV de datos")
    ap.add_argument("--port", type=int, default=5000, help="Puerto del servidor")
    args = ap.parse_args()

    global state

    print(f"⚡ CPS Attack Monitor")
    print(f"  Script: {args.script}")
    print(f"  Modelo: {args.pkl}")
    print(f"  Datos:  {args.csv}")
    print(f"  Ejecutando inferencia...")

    resultados = ejecutar_inferencia(args.script, args.pkl, args.csv)
    n_flags = sum(1 for r in resultados if r.get("flag") == 1)
    print(f"  → {len(resultados)} filas, {n_flags} ataques detectados")

    model_info = {
        "script": str(Path(args.script).name),
        "pkl": str(Path(args.pkl).name),
        "total": len(resultados),
        "flags": n_flags,
    }
    state = ReplayState(resultados, model_info)

    print(f"\n→ Abrí http://localhost:{args.port}\n")
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
