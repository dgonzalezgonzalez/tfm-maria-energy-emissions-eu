#!/usr/bin/env python3
import csv
import json
import os
import urllib.request
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("tmp/matplotlib-cache").resolve()))
os.environ.setdefault("XDG_CACHE_HOME", str(Path("tmp/xdg-cache").resolve()))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "env_air_gge?geo=ES&geo=EU27_2020&airpol=GHG&unit=MIO_T&src_crf=CRF1&sinceTimePeriod=1990"
)

RAW_PATH = Path("data/raw/eurostat_env_air_gge_es_eu27_crf1.json")
ABS_CSV_PATH = Path("data/processed/emisiones_energia_es_ue.csv")
IDX_CSV_PATH = Path("data/processed/emisiones_energia_es_ue_index.csv")
PLOT_PATH = Path("output/figures/emisiones_energia_es_ue_indice.png")
ABS_PC_CSV_PATH = Path("data/processed/emisiones_energia_es_vs_ue_promedio_pais_abs.csv")
ABS_PC_PLOT_PATH = Path("output/figures/emisiones_energia_es_vs_ue_promedio_pais_abs.png")


def compute_strides(sizes):
    strides = [1] * len(sizes)
    running = 1
    for i in range(len(sizes) - 1, -1, -1):
        strides[i] = running
        running *= sizes[i]
    return strides


def decode_linear_index(idx, sizes, strides):
    coords = []
    for size, stride in zip(sizes, strides):
        coords.append((idx // stride) % size)
    return coords


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if RAW_PATH.exists():
        payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    else:
        payload = fetch_json(URL)
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    ids = payload["id"]
    sizes = payload["size"]
    dim = payload["dimension"]
    values = payload["value"]

    strides = compute_strides(sizes)

    index_to_label = {}
    for dim_name in ids:
        cat = dim[dim_name]["category"]
        index_to_label[dim_name] = {v: k for k, v in cat["index"].items()}

    rows = []
    for k, v in values.items():
        lin = int(k)
        coords = decode_linear_index(lin, sizes, strides)
        rec = {}
        for dim_name, coord in zip(ids, coords):
            rec[dim_name] = index_to_label[dim_name][coord]
        rec["emissions_mio_t"] = float(v)
        rows.append(rec)

    filtered = [
        {
            "year": int(r["time"]),
            "geo": r["geo"],
            "emissions_mio_t": r["emissions_mio_t"],
        }
        for r in rows
        if r["geo"] in {"ES", "EU27_2020"}
    ]

    ABS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ABS_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "geo", "emissions_mio_t"])
        w.writeheader()
        for r in sorted(filtered, key=lambda x: (x["year"], x["geo"])):
            w.writerow(r)

    years_by_geo = {}
    for r in filtered:
        years_by_geo.setdefault(r["geo"], set()).add(r["year"])
    common_years = sorted(set.intersection(*years_by_geo.values()))
    base_year = common_years[0]

    base_by_geo = {}
    for geo in ("ES", "EU27_2020"):
        base_by_geo[geo] = next(
            r["emissions_mio_t"] for r in filtered if r["geo"] == geo and r["year"] == base_year
        )

    indexed = []
    for r in filtered:
        if r["year"] in common_years:
            idx = r["emissions_mio_t"] / base_by_geo[r["geo"]]
            indexed.append({"year": r["year"], "geo": r["geo"], "index_base1": idx})

    with IDX_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "geo", "index_base1"])
        w.writeheader()
        for r in sorted(indexed, key=lambda x: (x["year"], x["geo"])):
            w.writerow({"year": r["year"], "geo": r["geo"], "index_base1": f"{r['index_base1']:.6f}"})

    es = sorted([r for r in indexed if r["geo"] == "ES"], key=lambda x: x["year"])
    eu = sorted([r for r in indexed if r["geo"] == "EU27_2020"], key=lambda x: x["year"])

    plt.figure(figsize=(11, 6))
    plt.plot([r["year"] for r in es], [r["index_base1"] for r in es], label="España", linewidth=2.2)
    plt.plot([r["year"] for r in eu], [r["index_base1"] for r in eu], label="UE-27", linewidth=2.2)
    plt.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    plt.title("Evolución de emisiones GEI del sector energético (base=1 en 1990)")
    plt.xlabel("Año")
    plt.ylabel("Índice (base=1)")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.figtext(
        0.01,
        0.01,
        f"Fuente: Eurostat env_air_gge (CRF1, GHG, MIO_T). Updated: {payload.get('updated', 'NA')}",
        ha="left",
        fontsize=9,
    )
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(PLOT_PATH, dpi=180)
    plt.close()

    # Absolute comparison: Spain vs EU-27 average emissions per country.
    # We derive EU per-country average from official EU27_2020 aggregate divided by 27.
    abs_pc_rows = []
    for r in filtered:
        if r["geo"] == "ES":
            abs_pc_rows.append(
                {
                    "year": r["year"],
                    "series": "ES",
                    "emissions_mio_t": r["emissions_mio_t"],
                }
            )
        elif r["geo"] == "EU27_2020":
            abs_pc_rows.append(
                {
                    "year": r["year"],
                    "series": "EU27_AVG_PER_COUNTRY",
                    "emissions_mio_t": r["emissions_mio_t"] / 27.0,
                }
            )

    with ABS_PC_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "series", "emissions_mio_t"])
        w.writeheader()
        for r in sorted(abs_pc_rows, key=lambda x: (x["year"], x["series"])):
            w.writerow(
                {
                    "year": r["year"],
                    "series": r["series"],
                    "emissions_mio_t": f"{r['emissions_mio_t']:.6f}",
                }
            )

    es_abs = sorted([r for r in abs_pc_rows if r["series"] == "ES"], key=lambda x: x["year"])
    eu_avg_abs = sorted(
        [r for r in abs_pc_rows if r["series"] == "EU27_AVG_PER_COUNTRY"],
        key=lambda x: x["year"],
    )

    plt.figure(figsize=(11, 6))
    plt.plot([r["year"] for r in es_abs], [r["emissions_mio_t"] for r in es_abs], label="España", linewidth=2.2)
    plt.plot(
        [r["year"] for r in eu_avg_abs],
        [r["emissions_mio_t"] for r in eu_avg_abs],
        label="UE-27 promedio por país (total UE/27)",
        linewidth=2.2,
    )
    plt.title("Emisiones GEI del sector energético en términos absolutos")
    plt.xlabel("Año")
    plt.ylabel("Millones de toneladas CO2e")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.figtext(
        0.01,
        0.01,
        (
            "Fuente: Eurostat env_air_gge (CRF1, GHG, MIO_T). "
            "Promedio UE-27 calculado como agregado EU27_2020 / 27."
        ),
        ha="left",
        fontsize=9,
    )
    ABS_PC_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(ABS_PC_PLOT_PATH, dpi=180)
    plt.close()

    print(f"raw_json={RAW_PATH}")
    print(f"abs_csv={ABS_CSV_PATH}")
    print(f"idx_csv={IDX_CSV_PATH}")
    print(f"plot_png={PLOT_PATH}")
    print(f"abs_pc_csv={ABS_PC_CSV_PATH}")
    print(f"abs_pc_plot_png={ABS_PC_PLOT_PATH}")
    print(f"base_year={base_year}")
    print(f"rows_abs={len(filtered)} rows_idx={len(indexed)}")


if __name__ == "__main__":
    main()
