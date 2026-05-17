from flask import Flask, jsonify, request, send_from_directory
import json
import csv
import io
import os
from datetime import datetime

app = Flask(__name__, static_folder="static")
DATA_FILE = "data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"questions": [], "responses": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# --- Questions ---

@app.route("/api/questions", methods=["GET"])
def get_questions():
    return jsonify(load_data()["questions"])


@app.route("/api/questions", methods=["POST"])
def add_question():
    data = load_data()
    q = request.json
    q["id"] = str(int(datetime.now().timestamp() * 1000))
    data["questions"].append(q)
    save_data(data)
    return jsonify(q), 201


@app.route("/api/questions/<qid>", methods=["PUT"])
def update_question(qid):
    data = load_data()
    for i, q in enumerate(data["questions"]):
        if q["id"] == qid:
            updated = request.json
            updated["id"] = qid
            data["questions"][i] = updated
            save_data(data)
            return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.route("/api/questions/<qid>", methods=["DELETE"])
def delete_question(qid):
    data = load_data()
    data["questions"] = [q for q in data["questions"] if q["id"] != qid]
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/questions/reorder", methods=["POST"])
def reorder_questions():
    data = load_data()
    order = request.json  # list of ids
    id_map = {q["id"]: q for q in data["questions"]}
    data["questions"] = [id_map[i] for i in order if i in id_map]
    save_data(data)
    return jsonify({"ok": True})


# --- Responses ---

@app.route("/api/responses", methods=["POST"])
def submit_response():
    data = load_data()
    resp = {
        "id": str(int(datetime.now().timestamp() * 1000)),
        "submitted_at": datetime.now().isoformat(),
        "answers": request.json,
    }
    data["responses"].append(resp)
    save_data(data)
    return jsonify({"ok": True}), 201


@app.route("/api/stats", methods=["GET"])
def get_stats():
    data = load_data()
    questions = data["questions"]
    responses = data["responses"]
    stats = []
    for q in questions:
        qid = q["id"]
        answers = [r["answers"].get(qid) for r in responses if qid in r["answers"]]
        if q["type"] in ("radio", "checkbox", "select"):
            counts = {}
            for a in answers:
                if isinstance(a, list):
                    for item in a:
                        counts[item] = counts.get(item, 0) + 1
                elif a:
                    counts[a] = counts.get(a, 0) + 1
            stats.append({"id": qid, "title": q["title"], "type": q["type"], "counts": counts, "total": len(answers)})
        else:
            stats.append({"id": qid, "title": q["title"], "type": q["type"], "answers": answers, "total": len(answers)})
    return jsonify({"total_responses": len(responses), "questions": stats})


@app.route("/api/export", methods=["GET"])
def export_csv():
    data = load_data()
    questions = data["questions"]
    responses = data["responses"]
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["提交时间"] + [q["title"] for q in questions]
    writer.writerow(headers)
    for r in responses:
        row = [r["submitted_at"]]
        for q in questions:
            ans = r["answers"].get(q["id"], "")
            row.append(", ".join(ans) if isinstance(ans, list) else ans)
        writer.writerow(row)
    from flask import Response
    return Response(
        "﻿" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=responses.csv"},
    )


if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(debug=True, port=5000)
