# Emisiones del sector energético: España vs UE-27

Fuente oficial: Eurostat (`env_air_gge`, Comisión Europea).

## Qué incluye
- Descarga oficial en JSON: `data/raw/eurostat_env_air_gge_es_eu27_crf1.json`
- Serie absoluta (Mt CO2e): `data/processed/emisiones_energia_es_ue.csv`
- Serie normalizada (base=1 en 1990): `data/processed/emisiones_energia_es_ue_index.csv`
- Gráfico comparado: `output/figures/emisiones_energia_es_ue_indice.png`

## Método
- Filtro: `geo=ES,EU27_2020`, `airpol=GHG`, `src_crf=CRF1`, `unit=MIO_T`
- Normalización: `index_t = emisiones_t / emisiones_1990` para cada serie
- Cobertura temporal obtenida: 1990-2023

## Reproducir
```bash
python3 scripts/fetch_process_plot_emissions.py
```

## Resultado rápido
- España: índice 2023 = 0.958633 (vs 1990 = 1)
- UE-27: índice 2023 = 0.632065 (vs 1990 = 1)
