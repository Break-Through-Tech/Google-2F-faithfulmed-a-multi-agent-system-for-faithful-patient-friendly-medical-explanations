"""Offline plumbing demo: python -m baseline --demo (no model or network calls)."""
import argparse
import json

from .pipeline import BaselineInput, run_baseline


class DemoCollection:
    def query(self, **kwargs):
        return {
            "ids": [["synthetic-definition-1"]],
            "documents": [["Hypertension means high blood pressure."]],
            "metadatas": [[{"source": "synthetic demo fixture"}]],
            "distances": [[0.0]],
        }


class DemoGenerator:
    model = "offline-stub-not-gemini"

    def generate(self, **kwargs):
        return "Your note says you have high blood pressure. Follow up in two weeks."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True)
    parser.parse_args()
    result = run_baseline(
        BaselineInput("synthetic-demo-1", "Hypertension. Follow up in two weeks."),
        collection=DemoCollection(), generator=DemoGenerator(), top_k=1,
    )
    result["demo"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
