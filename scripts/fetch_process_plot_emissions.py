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
URL_SECTOR_SHARES = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "env_air_gge?geo=ES&geo=EU27_2020&airpol=GHG&unit=MIO_T&sinceTimePeriod=1990"
    "&src_crf=CRF1&src_crf=CRF2&src_crf=CRF3&src_crf=CRF5&src_crf=TOTX4_MEMO"
)

RAW_PATH = Path("data/raw/eurostat_env_air_gge_es_eu27_crf1.json")
RAW_SECTOR_SHARES_PATH = Path("data/raw/eurostat_env_air_gge_sector_shares_es_eu_series.json")
ABS_CSV_PATH = Path("data/processed/emisiones_energia_es_ue.csv")
IDX_CSV_PATH = Path("data/processed/emisiones_energia_es_ue_index.csv")
PLOT_PATH = Path("output/figures/emisiones_energia_es_ue_indice.png")
ABS_PC_CSV_PATH = Path("data/processed/emisiones_energia_es_vs_ue_promedio_pais_abs.csv")
ABS_PC_PLOT_PATH = Path("output/figures/emisiones_energia_es_vs_ue_promedio_pais_abs.png")
SECTOR_SHARE_CSV_PATH = Path("data/processed/contribucion_sectorial_es_ue_2023.csv")
SECTOR_SHARE_PLOT_PATH = Path("output/figures/contribucion_sector_energetico_mayor_es_ue.png")
SECTOR_SHARE_TS_CSV_PATH = Path("data/processed/contribucion_sectorial_es_ue_series.csv")
SECTOR_SHARE_TS_PLOT_PATH = Path("output/figures/contribucion_sectorial_evolucion_es_ue.png")


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

    if RAW_SECTOR_SHARES_PATH.exists():
        payload_shares = json.loads(RAW_SECTOR_SHARES_PATH.read_text(encoding="utf-8"))
    else:
        payload_shares = fetch_json(URL_SECTOR_SHARES)
        RAW_SECTOR_SHARES_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_SECTOR_SHARES_PATH.write_text(
            json.dumps(payload_shares, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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

    # Sector contribution shares (economic sectors): CRF1/2/3/5 over TOTX4_MEMO.
    ids_s = payload_shares["id"]
    sizes_s = payload_shares["size"]
    dim_s = payload_shares["dimension"]
    values_s = payload_shares["value"]
    strides_s = compute_strides(sizes_s)

    index_to_label_s = {}
    for dim_name in ids_s:
        cat = dim_s[dim_name]["category"]
        index_to_label_s[dim_name] = {v: k for k, v in cat["index"].items()}

    rows_s = []
    for k, v in values_s.items():
        lin = int(k)
        coords = decode_linear_index(lin, sizes_s, strides_s)
        rec = {}
        for dim_name, coord in zip(ids_s, coords):
            rec[dim_name] = index_to_label_s[dim_name][coord]
        rec["emissions_mio_t"] = float(v)
        rows_s.append(rec)

    sector_labels = {
        "CRF1": "Energía",
        "CRF2": "Procesos industriales",
        "CRF3": "Agricultura",
        "CRF5": "Residuos",
    }
    total_code = "TOTX4_MEMO"

    totals = {}
    for r in rows_s:
        if r["src_crf"] == total_code:
            totals[(r["geo"], int(r["time"]))] = r["emissions_mio_t"]

    share_rows = []
    for r in rows_s:
        src = r["src_crf"]
        if src not in sector_labels:
            continue
        geo = r["geo"]
        year = int(r["time"])
        total = totals.get((geo, year))
        if total is None or total == 0:
            continue
        share = 100.0 * r["emissions_mio_t"] / total
        share_rows.append(
            {
                "year": year,
                "geo": geo,
                "sector_code": src,
                "sector": sector_labels[src],
                "emissions_mio_t": r["emissions_mio_t"],
                "total_mio_t": total,
                "share_pct": share,
            }
        )

    with SECTOR_SHARE_TS_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "geo",
                "sector_code",
                "sector",
                "emissions_mio_t",
                "total_mio_t",
                "share_pct",
            ],
        )
        w.writeheader()
        for r in sorted(share_rows, key=lambda x: (x["geo"], x["year"], x["sector_code"])):
            w.writerow(
                {
                    "year": r["year"],
                    "geo": r["geo"],
                    "sector_code": r["sector_code"],
                    "sector": r["sector"],
                    "emissions_mio_t": f"{r['emissions_mio_t']:.6f}",
                    "total_mio_t": f"{r['total_mio_t']:.6f}",
                    "share_pct": f"{r['share_pct']:.4f}",
                }
            )

    target_year = max(int(r["time"]) for r in rows_s)
    share_rows_target = [r for r in share_rows if r["year"] == target_year]
    with SECTOR_SHARE_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "geo",
                "sector_code",
                "sector",
                "emissions_mio_t",
                "total_mio_t",
                "share_pct",
            ],
        )
        w.writeheader()
        for r in sorted(share_rows_target, key=lambda x: (x["geo"], x["sector_code"])):
            w.writerow(
                {
                    "year": r["year"],
                    "geo": r["geo"],
                    "sector_code": r["sector_code"],
                    "sector": r["sector"],
                    "emissions_mio_t": f"{r['emissions_mio_t']:.6f}",
                    "total_mio_t": f"{r['total_mio_t']:.6f}",
                    "share_pct": f"{r['share_pct']:.4f}",
                }
            )

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    for ax, geo, title in [
        (axes[0], "ES", "España"),
        (axes[1], "EU27_2020", "UE-27"),
    ]:
        data_geo = [r for r in share_rows if r["geo"] == geo and r["year"] == target_year]
        data_geo.sort(key=lambda x: x["share_pct"], reverse=True)
        sectors = [r["sector"] for r in data_geo]
        shares = [r["share_pct"] for r in data_geo]
        colors = ["#d62728" if r["sector_code"] == "CRF1" else "#9aa0a6" for r in data_geo]
        bars = ax.barh(sectors, shares, color=colors)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel("% sobre total (excl. LULUCF)")
        for b, s in zip(bars, shares):
            ax.text(b.get_width() + 0.3, b.get_y() + b.get_height() / 2, f"{s:.1f}%", va="center", fontsize=9)

    fig.suptitle(f"Contribución sectorial a emisiones totales ({target_year})")
    plt.figtext(
        0.01,
        0.01,
        (
            "Fuente: Eurostat env_air_gge. Total = TOTX4_MEMO "
            "(excluye LULUCF y memo items). Energía (CRF1) resaltada."
        ),
        ha="left",
        fontsize=9,
    )
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    SECTOR_SHARE_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SECTOR_SHARE_PLOT_PATH, dpi=180)
    plt.close()

    # Evolution chart of sector contributions over time (ES and EU-27).
    color_map = {
        "CRF1": "#d62728",  # highlight energy
        "CRF2": "#1f77b4",
        "CRF3": "#2ca02c",
        "CRF5": "#9467bd",
    }
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.8), sharey=True)
    legend_labels_ts = {
        "CRF1": "Energía",
        "CRF2": "Procesos Industriales",
        "CRF3": "Agricultura",
        "CRF5": "Residuos",
    }
    for ax, geo, title in [
        (axes[0], "ES", "España"),
        (axes[1], "EU27_2020", "UE-27"),
    ]:
        for code in ("CRF1", "CRF2", "CRF3", "CRF5"):
            series = sorted(
                [r for r in share_rows if r["geo"] == geo and r["sector_code"] == code],
                key=lambda x: x["year"],
            )
            ax.plot(
                [r["year"] for r in series],
                [r["share_pct"] for r in series],
                label=legend_labels_ts[code],
                color=color_map[code],
                linewidth=2.2 if code == "CRF1" else 1.8,
            )
        ax.set_title(title)
        ax.set_xlabel("Año")
        ax.grid(alpha=0.25)

    axes[0].set_ylabel("% sobre total (excl. LULUCF)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.015),
        ncol=2,
        frameon=False,
        columnspacing=4.0,
        handletextpad=1.0,
        borderaxespad=0.8,
        fontsize=11,
    )
    fig.suptitle("Evolución de contribuciones sectoriales a emisiones totales", y=0.97)
    plt.figtext(
        0.01,
        0.01,
        (
            "Fuente: Eurostat env_air_gge. Denominador: TOTX4_MEMO "
            "(excluye LULUCF y memo items)."
        ),
        ha="left",
        fontsize=9,
    )
    plt.tight_layout(rect=[0, 0.16, 1, 0.92])
    SECTOR_SHARE_TS_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SECTOR_SHARE_TS_PLOT_PATH, dpi=180)
    plt.close()

    print(f"raw_json={RAW_PATH}")
    print(f"abs_csv={ABS_CSV_PATH}")
    print(f"idx_csv={IDX_CSV_PATH}")
    print(f"plot_png={PLOT_PATH}")
    print(f"abs_pc_csv={ABS_PC_CSV_PATH}")
    print(f"abs_pc_plot_png={ABS_PC_PLOT_PATH}")
    print(f"sector_share_raw_json={RAW_SECTOR_SHARES_PATH}")
    print(f"sector_share_csv={SECTOR_SHARE_CSV_PATH}")
    print(f"sector_share_plot_png={SECTOR_SHARE_PLOT_PATH}")
    print(f"sector_share_ts_csv={SECTOR_SHARE_TS_CSV_PATH}")
    print(f"sector_share_ts_plot_png={SECTOR_SHARE_TS_PLOT_PATH}")
    print(f"base_year={base_year}")
    print(f"rows_abs={len(filtered)} rows_idx={len(indexed)}")


if __name__ == "__main__":
    main()
