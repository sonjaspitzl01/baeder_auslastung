"""
Sammelt die aktuelle Auslastung der LINZ AG Bäder und hängt sie an data/auslastung.csv an.
Läuft per GitHub Action alle 15 Minuten (siehe .github/workflows/collect.yml).

Die API liefert pro Bad-ID z. B.:  [{"id":20,"relativeCurrCapacity":42}]
Weitere Bäder: in den DevTools die anderen /utilisation/<ID>-Requests suchen
und unten in BAEDER ergänzen (ID → Name, wie er auf der Website erscheinen soll).
"""
import csv, json, sys, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_URL = "https://www.linzag.at/RESTfulBaths/rest/utilisation/{id}"
BAEDER = {
    1: "Biesenfeldbad",
}
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "auslastung.csv"
TZ = ZoneInfo("Europe/Vienna")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (privater Auslastungs-Logger)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def extract(raw: str) -> float | None:
    """Liest relativeCurrCapacity (Prozent) aus der Antwort."""
    data = json.loads(raw)
    eintrag = data[0] if isinstance(data, list) and data else data
    wert = eintrag.get("relativeCurrCapacity")
    return float(wert) if wert is not None else None


def main():
    werte = {}
    for bad_id, name in BAEDER.items():
        try:
            raw = fetch(SOURCE_URL.format(id=bad_id))
            if "--debug" in sys.argv:
                print(bad_id, raw[:500])
            wert = extract(raw)
            if wert is not None:
                werte[name] = wert
        except Exception as e:  # ein Bad mit Fehler soll die anderen nicht blockieren
            print(f"Fehler bei ID {bad_id}: {e}", file=sys.stderr)

    if not werte:
        sys.exit("Keine Werte gefunden – Format geändert? Mit --debug prüfen.")

    jetzt = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
    neu = not CSV_PATH.exists()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(["zeit", "bad", "auslastung"])
        for bad, wert in werte.items():
            w.writerow([jetzt, bad, round(wert, 1)])
    print(f"{jetzt}: {werte}")


if __name__ == "__main__":
    main()
