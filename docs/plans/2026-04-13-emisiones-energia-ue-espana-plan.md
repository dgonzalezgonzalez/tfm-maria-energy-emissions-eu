# Plan: Emisiones sector energético España vs UE (índice base=1)
Created: 2026-04-13

## Objetivo
- Descargar datos oficiales de emisiones GEI del sector energético.
- Construir serie temporal comparable: España vs conjunto UE.
- Graficar evolución normalizada (índice = emisiones / emisiones del primer año disponible).

## Fuente oficial seleccionada
- Proveedor: Eurostat (Comisión Europea), dataset `env_air_gge`.
- Dataset: *Greenhouse gas emissions by source sector*.
- API base: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/env_air_gge
- Actualización reportada por API: `2025-05-08T23:00:00+0200`.

## Definición de serie
- Geografías: `ES` (España), `EU27_2020` (UE-27).
- Contaminante: `GHG`.
- Sector: `src_crf=CRF1` (total sector energía, clasificación CRF/UNFCCC).
- Unidad: `MIO_T` (millones de toneladas CO2 equivalente).
- Frecuencia: anual (`A`).
- Ventana temporal objetivo: 1990-2023 (si API devuelve menos, usar rango devuelto).

## Supuestos
- “Sector energético” se interpreta como agregado CRF1 (no solo industrias energéticas CRF1A1).
- Comparación principal con total UE-27, no promedio por país.
- Normalización base al primer año común de la serie.

## Pasos de ejecución
1. Descargar datos
- Query recomendada:
  - `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/env_air_gge?geo=ES&geo=EU27_2020&airpol=GHG&unit=MIO_T&src_crf=CRF1&sinceTimePeriod=1990`
- Guardar crudo en `data/raw/eurostat_env_air_gge_es_eu27_crf1.json`.

2. Transformar a tabla larga
- Campos mínimos: `year`, `geo`, `emissions_mio_t`.
- Salida limpia: `data/processed/emisiones_energia_es_ue.csv`.

3. Alinear años y controlar faltantes
- Intersección de años entre `ES` y `EU27_2020`.
- Si falta algún año intermedio: no interpolar; dejar hueco y documentar.

4. Construir índice base=1
- Para cada serie (`geo`):
  - `index_t = emissions_t / emissions_base`.
  - `emissions_base`: valor del primer año común.
- Salida: `data/processed/emisiones_energia_es_ue_index.csv`.

5. Graficar
- Eje X: año.
- Eje Y: índice (base=1).
- 2 líneas: España, UE-27.
- Añadir línea horizontal en 1.0.
- Título sugerido: “Evolución de emisiones GEI del sector energético (base=1 en año inicial)”.
- Nota de fuente en pie: “Eurostat env_air_gge (CRF1, GHG, MIO_T)”.
- Exportar en `output/figures/emisiones_energia_es_ue_indice.png`.

6. Verificación rápida
- Check 1: primer año ambas series = 1 exacto.
- Check 2: años en gráfico = años en CSV índice.
- Check 3: leyenda y unidades coherentes con fuente.

## Entregables
- Datos crudos JSON.
- CSV limpio niveles absolutos.
- CSV índice normalizado.
- Gráfico PNG final.
- Nota metodológica breve (3-5 líneas) con definición de CRF1 y año base.

## Riesgos y mitigación
- Riesgo: ambigüedad “sector energético” (CRF1 vs CRF1A1).
- Mitigación: usar CRF1 como principal; opcional anexo sensibilidad con CRF1A1.

- Riesgo: quiebre de comparabilidad por cambios de cobertura UE.
- Mitigación: fijar `EU27_2020` en toda la serie y explicitar en nota.

## Opción alternativa (si se prefiere)
- Repetir mismo flujo con `src_crf=CRF1A1` (solo industrias energéticas) y comparar robustez visual.
