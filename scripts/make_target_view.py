"""Generate a lightweight NGL HTML view of 6ARU with epitope patches.

Reads data/processed/epitope_candidates.csv and writes
reports/target_view.html. Requires internet in the browser (NGL from
jsdelivr CDN, structure from RCSB). 6ARU auth numbering = UniProt - 24
(verified in residue_map.meta.json).

Run: .venv/bin/python scripts/make_target_view.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

PATCH_COLORS = ["orange", "lime", "magenta", "cyan"]


def main() -> int:
    cands = list(csv.DictReader(open(OUT / "epitope_candidates.csv")))
    patches = []
    for i, c in enumerate(cands):
        a_lo = int(c["uniprot_begin"]) - 24
        a_hi = int(c["uniprot_end"]) - 24
        patches.append(
            {
                "id": c["candidate_id"],
                "uniprot": f"{c['uniprot_begin']}-{c['uniprot_end']}",
                "auth": f"{a_lo}-{a_hi}",
                "color": PATCH_COLORS[i % len(PATCH_COLORS)],
            }
        )

    patch_js = json.dumps(patches)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>6ARU EGFR ECD - epitope candidates</title>
<script src="https://cdn.jsdelivr.net/npm/ngl@2/dist/ngl.js"></script>
<style>
 body {{ font-family: sans-serif; margin: 0; display: flex; height: 100vh; }}
 #viewport {{ flex: 1; }}
 #panel {{ width: 320px; padding: 12px; overflow: auto; background: #f7f7f7; }}
 .swatch {{ display: inline-block; width: 12px; height: 12px; margin-right: 6px; }}
 code {{ font-size: 12px; }}
</style>
</head>
<body>
<div id="viewport"></div>
<div id="panel">
  <h3>6ARU chain A (EGFR ECD)</h3>
  <p>Auth numbering = UniProt P00533 &minus; 24. Domain III (auth 286-457,
  UniProt 310-481) shown in blue. Cetuximab Fab chains B/C in yellow surface;
  glycan chains D-H in red sticks.</p>
  <div id="legend"></div>
  <p><small>Internet required: NGL via jsdelivr, structure via rcsb://6ARU.
  Generated {__import__('datetime').datetime.now():%Y-%m-%d}.</small></p>
</div>
<script>
var patches = {patch_js};
var stage = new NGL.Stage("viewport", {{backgroundColor: "white"}});
stage.loadFile("rcsb://6ARU").then(function (o) {{
  o.addRepresentation("cartoon", {{sele: ":A", color: "lightgrey"}});
  o.addRepresentation("cartoon", {{sele: ":A and 286-457", color: "blue"}});
  o.addRepresentation("surface", {{sele: ":B or :C", color: "yellow", opacity: 0.35}});
  o.addRepresentation("licorice", {{sele: ":D or :E or :F or :G or :H", color: "red"}});
  var legend = document.getElementById("legend");
  patches.forEach(function (p) {{
    o.addRepresentation("spacefill", {{sele: ":A and " + p.auth, color: p.color}});
    var div = document.createElement("div");
    div.innerHTML = "<span class='swatch' style='background:" + p.color + "'></span>" +
      "<b>" + p.id + "</b> UniProt " + p.uniprot + " (auth " + p.auth + ")";
    legend.appendChild(div);
  }});
  o.autoView();
}});
</script>
</body>
</html>
"""
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "target_view.html").write_text(html)
    print(f"wrote {REPORTS / 'target_view.html'} with {len(patches)} patches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
