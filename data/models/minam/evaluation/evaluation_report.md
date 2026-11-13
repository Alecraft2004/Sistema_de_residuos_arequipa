# Evaluación del modelo MINAM — 2024

Modelo evaluado: baseline de persistencia (`generacion_lag_1`).
Esta evaluación es posterior al entrenamiento y no cambia la selección del modelo.

## Métricas nacionales

- Observaciones: 1891
- MAE: 290.8381 toneladas/año
- RMSE: 1904.5767 toneladas/año
- R²: 0.991535

## Arequipa

- Observaciones: 109
- MAE: 427.9126
- RMSE: 2070.3822
- R²: 0.949369

## Sesgo y residuos

- Sesgo medio (predicción - real): -152.5782
- Mediana del residuo: 0.1300
- Sobreestimaciones: 964
- Subestimaciones: 920
- P95 del error absoluto: 743.6950

## Concentración en valores reales altos

- Umbral del 10% superior: 7685.8200
- MAE del 10% superior: 2483.3861
- MAE del resto: 45.9327
- Participación del error absoluto: 85.79%

## Limitaciones

- La persistencia no aprende relaciones adicionales entre población, territorio y generación.
- Los distritos con historial corto tienen menos información histórica.
- El error de distritos grandes puede dominar RMSE y el error absoluto agregado.
- R² no debe interpretarse como única medida de calidad.
- Los resultados no establecen causalidad.
