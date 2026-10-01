"""Generate the Stage-1.5 NGL HTML viewer of 6ARU (Part I).

Elements: Domain III surface; Scheme 1 (EPI_H_2 + EPI_H_3), Scheme 2
(EPI_H_1); H370/H418/H433; glycan-anchor Asn sites N352/361/413/444;
glycan chains D-H; Cetuximab Fab translucent. Five preset views.
Auth numbering = UniProt - 24 (residue_map.meta.json).

Run: .venv/bin/python scripts/make_target_view.py
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OFFSET = 24


def arng(lo_hi_uniprot: str) -> str:
    lo, hi = (int(x) for x in lo_hi_uniprot.split("-"))
    return f"{lo - OFFSET}-{hi - OFFSET}"


def main() -> int:
    cands = {c["candidate_id"]: f"{c['uniprot_begin']}-{c['uniprot_end']}"
             for c in csv.DictReader(open(OUT / "epitope_candidates.csv"))}
    e1 = arng(cands["EPI_H_1"])
    e2 = arng(cands["EPI_H_2"])
    e3 = arng(cands["EPI_H_3"])
    d3 = f"{310 - OFFSET}-{481 - OFFSET}"
    h370, h418, h433 = 370 - OFFSET, 418 - OFFSET, 433 - OFFSET
    n352, n361, n413, n444 = (n - OFFSET for n in (352, 361, 413, 444))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>6ARU EGFR - Stage 1.5 target/epitope audit view</title>
<script src="https://cdn.jsdelivr.net/npm/ngl@2/dist/ngl.js"></script>
<style>
 body {{ font-family: sans-serif; margin: 0; display: flex; height: 100vh; }}
 #viewport {{ flex: 1; }}
 #panel {{ width: 340px; padding: 12px; overflow: auto; background: #f7f7f7; font-size: 13px; }}
 button {{ display: block; width: 100%; margin: 4px 0; padding: 6px; cursor: pointer; }}
 .swatch {{ display: inline-block; width: 12px; height: 12px; margin-right: 6px; }}
 h4 {{ margin: 12px 0 4px; }}
 code {{ font-size: 11px; }}
</style>
</head>
<body>
<div id="viewport"></div>
<div id="panel">
  <h3>6ARU chain A - Stage 1.5 audit</h3>
  <p>Auth = UniProt &minus; 24. Domain III <code>{d3}</code> white surface;
  other EGFR domains light grey; Cetuximab Fab B/C translucent yellow;
  glycan chains D-H red.</p>
  <h4>Preset views</h4>
  <button onclick="focusSel(':A and {d3}')">1. Overall Domain III</button>
  <button onclick="focusSel(':A and ({e2} or {e3})')">2. Scheme 1 close-up</button>
  <button onclick="focusSel(':A and ({n352},{n361},{n413},{n444},{e2.split('-')[0]}-{e3.split('-')[1]}) or :D or :E or :F or :G or :H')">3. Glycan-risk view</button>
  <button onclick="focusSel(':A and ({h370},{h418},{h433})')">4. H433 / pH hotspot</button>
  <button onclick="focusSel(':A and {e2.split('-')[0]}-{h433} or :B or :C')">5. Cetuximab-overlap view</button>
  <h4>Legend</h4>
  <div id="legend"></div>
  <p><small>Internet required (NGL via jsdelivr, rcsb://6ARU). Generated {date.today()}.</small></p>
</div>
<script>
var SEL = {{
  d3: ":A and {d3}",
  e1: ":A and {e1}",
  e2: ":A and {e2}",
  e3: ":A and {e3}",
  h370: ":A and {h370}",
  h418: ":A and {h418}",
  h433: ":A and {h433}",
  glyAsn: ":A and ({n352},{n361},{n413},{n444})",
  fab: ":B or :C",
  gly: ":D or :E or :F or :G or :H"
}};
var LEGEND = [
  ["orange", "Scheme 1: EPI_H_2 (U385-403, auth {e2})"],
  ["lime", "Scheme 1: EPI_H_3 (U416-431, auth {e3})"],
  ["magenta", "Scheme 2: EPI_H_1 (U316-343, auth {e1})"],
  ["red", "H433 (pH mechanism B candidate, U433)"],
  ["purple", "H370 (partially exposed, U370)"],
  ["grey", "H418 (buried, U418)"],
  ["yellow", "N-glycan anchors N352/361/413/444"],
  ["salmon", "glycan atoms D-H (6ARU deposited)"],
  ["#ffff66", "Cetuximab Fab B/C (translucent)"]
];
var legend = document.getElementById("legend");
LEGEND.forEach(function (x) {{
  var d = document.createElement("div");
  d.innerHTML = "<span class='swatch' style='background:" + x[0] + "'></span>" + x[1];
  legend.appendChild(d);
}});

var stage = new NGL.Stage("viewport", {{backgroundColor: "white"}});
var comp;
stage.loadFile("rcsb://6ARU").then(function (o) {{
  comp = o;
  o.addRepresentation("cartoon", {{sele: ":A", color: "lightgrey"}});
  o.addRepresentation("surface", {{sele: SEL.d3, color: "white", opacity: 0.85,
                                  surfaceType: "av"}});
  o.addRepresentation("spacefill", {{sele: SEL.e2, color: "orange"}});
  o.addRepresentation("spacefill", {{sele: SEL.e3, color: "lime"}});
  o.addRepresentation("spacefill", {{sele: SEL.e1, color: "magenta"}});
  o.addRepresentation("spacefill", {{sele: SEL.h433, color: "red", radius: 1.4}});
  o.addRepresentation("spacefill", {{sele: SEL.h370, color: "purple", radius: 1.2}});
  o.addRepresentation("spacefill", {{sele: SEL.h418, color: "grey", radius: 1.0}});
  o.addRepresentation("spacefill", {{sele: SEL.glyAsn, color: "yellow", radius: 1.2}});
  o.addRepresentation("licorice", {{sele: SEL.gly, color: "salmon", radius: 1.6}});
  o.addRepresentation("surface", {{sele: SEL.fab, color: "yellow", opacity: 0.25}});
  o.addRepresentation("cartoon", {{sele: SEL.fab, color: "yellow"}});
  o.autoView(SEL.d3);
}});
function focusSel(sel) {{ if (comp) comp.autoView(sel, 900); }}
window.addEventListener("resize", function () {{ stage.handleResize(); }});
</script>
</body>
</html>
"""
    (REPORTS / "target_view.html").write_text(html)
    print(f"wrote {REPORTS / 'target_view.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
