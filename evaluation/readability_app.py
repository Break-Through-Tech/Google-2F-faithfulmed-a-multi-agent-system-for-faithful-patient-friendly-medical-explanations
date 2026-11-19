"""Local browser UI for trying the readability scorer.

Run from the repository root with ``python -m evaluation.readability_app``.
The server binds to localhost and does not send text to an external service.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from evaluation.readability import evaluate_readability

MAX_BODY_BYTES = 100_000
PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FaithfulMed Readability Tester</title>
  <style>
    :root { color-scheme: light; font: 16px/1.5 system-ui, sans-serif; }
    body { max-width: 760px; margin: 3rem auto; padding: 0 1rem; color: #17212b; }
    h1 { margin-bottom: .25rem; }
    .hint { margin-top: 0; color: #526170; }
    textarea { box-sizing: border-box; width: 100%; min-height: 12rem; padding: .8rem;
      font: inherit; border: 1px solid #9aa8b5; border-radius: .5rem; }
    label { display: block; margin: 1rem 0 .25rem; font-weight: 600; }
    input { width: 8rem; padding: .45rem; font: inherit; }
    button { margin-top: 1rem; padding: .65rem 1rem; font: inherit; font-weight: 600;
      color: white; background: #155eef; border: 0; border-radius: .4rem; cursor: pointer; }
    button:disabled { opacity: .6; cursor: wait; }
    #result { margin-top: 1.5rem; padding: 1rem; border-radius: .5rem; background: #f2f5f8; }
    #result[hidden] { display: none; }
    #status { font-size: 1.2rem; font-weight: 700; }
    .error { color: #b42318; }
    dl { display: grid; grid-template-columns: minmax(12rem, 1fr) 2fr; gap: .35rem 1rem; }
    dt { color: #526170; } dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
    footer { margin-top: 2rem; color: #526170; font-size: .9rem; }
  </style>
</head>
<body>
  <h1>Readability Tester</h1>
  <p class="hint">Score a draft locally with FaithfulMed's readability evaluator.
     Text stays on this computer and is not sent to an AI model.</p>
  <form id="form">
    <label for="text">Explanation text</label>
    <textarea id="text" required placeholder="Paste a patient-friendly explanation here"></textarea>
    <label for="grade">Maximum Flesch-Kincaid grade</label>
    <input id="grade" type="number" min="0" max="20" step="0.5" value="8">
    <label for="max-words">Maximum word count (optional)</label>
    <input id="max-words" type="number" min="1" max="10000" placeholder="No limit">
    <br><button id="submit" type="submit">Score text</button>
  </form>
  <section id="result" aria-live="polite" hidden>
    <div id="status"></div>
    <p id="error" class="error"></p>
    <dl id="metrics"></dl>
  </section>
  <footer>Scores are heuristics, not medical or clinical approval.</footer>
  <script>
    const form = document.querySelector("#form");
    const submit = document.querySelector("#submit");
    const result = document.querySelector("#result");
    const status = document.querySelector("#status");
    const error = document.querySelector("#error");
    const metrics = document.querySelector("#metrics");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.hidden = false;
      status.textContent = "Scoring…";
      error.textContent = "";
      metrics.replaceChildren();
      submit.disabled = true;
      const maxWords = document.querySelector("#max-words").value;
      try {
        const response = await fetch("/score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: document.querySelector("#text").value,
            max_grade: Number(document.querySelector("#grade").value),
            max_words: maxWords === "" ? null : Number(maxWords),
          }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Scoring failed.");
        const score = data.score;
        if (score.status !== "ok") throw new Error(score.error || "Could not score this text.");
        status.textContent = score.passes_readability
          ? "Passes readability target"
          : "Does not pass readability target";
        const entries = [
          ["Flesch-Kincaid grade", score.flesch_kincaid_grade],
          ["SMOG grade", score.smog_grade ?? "Not available (requires 3+ sentences)"],
          ["Words", score.word_count],
          ["Sentences", score.sentence_count],
          ["Medical jargon count", score.medical_jargon_count],
          ["Medical jargon density", score.medical_jargon_density],
          ["Medical terms found", score.medical_terms_found || "None detected"],
          ["Refusal detected", score.is_refusal ? "Yes" : "No"],
          ["Grade target", score.passes_grade_target ? "Pass" : "Fail"],
          ["Length target", score.passes_length_target ? "Pass" : "Fail"],
        ];
        for (const [label, value] of entries) {
          const term = document.createElement("dt");
          const detail = document.createElement("dd");
          term.textContent = label;
          detail.textContent = value;
          metrics.append(term, detail);
        }
      } catch (exception) {
        status.textContent = "Could not score text";
        error.textContent = exception.message;
      } finally {
        submit.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


class ReadabilityHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/score":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request length."})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "Request must contain up to 100 KB of JSON."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            text = payload["text"]
            max_grade = payload.get("max_grade", 8)
            max_words = payload.get("max_words")
            if not isinstance(text, str):
                raise ValueError("Text must be a string.")
            if isinstance(max_grade, bool) or not isinstance(max_grade, (int, float)):
                raise ValueError("Maximum grade must be a number.")
            if not 0 <= max_grade <= 20:
                raise ValueError("Maximum grade must be between 0 and 20.")
            if max_words is not None and (
                isinstance(max_words, bool)
                or not isinstance(max_words, int)
                or not 1 <= max_words <= 10_000
            ):
                raise ValueError("Maximum words must be a whole number between 1 and 10,000.")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc) or "Invalid request."})
            return

        score = evaluate_readability(text, max_grade=max_grade, max_words=max_words)
        self.send_json(200, {"score": score})

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


def main():
    parser = argparse.ArgumentParser(description="Run the local readability tester UI.")
    parser.add_argument("--port", type=int, default=8765, help="Local port (default: 8765)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ReadabilityHandler)
    print(f"Readability Tester running at http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Readability Tester.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
