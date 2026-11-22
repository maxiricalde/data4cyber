# sin-profile-supervisado

Objetivo: el detector supervisado (notebook 02, `src/`, resultados supervisados y bundle) excluye `Profile.*` de las features. La fuga se documenta al inicio del notebook como advertencia, no como feature.
Branch: `main`. Runner: `.venv/bin/python`.

## Specs

- **S1.** El detector supervisado excluye `Profile.*` de la matriz de features (139 → 132 columnas).
- **S2.** Al inicio del notebook 02 se muestra qué pasa si se incluye `Profile.*` (la fuga: congelado en S0, variable en S1–S6, AUC 0,988 separando escenarios), como advertencia.
- **S3.** El EDA (notebook 01) sigue hablando de `Profile.*`: es donde se identifica la fuga. No se toca.
- **S4.** El no supervisado (notebook 03) queda como está (con `Profile.*`); se resuelve aparte.
- **S5.** No se borra ninguna columna de los datos crudos: solo se excluye `Profile.*` de la matriz de features.
- **S6.** Los resultados y el bundle supervisados se regeneran sin `Profile.*`.

## Tasks

| ID | Spec | Ruta | Estado | Evidencia |
| --- | --- | --- | --- | --- |
| T1 | S1 | inline | hecho | `build_matrices(include_profile=False)` elimina las 7 columnas `Profile.*` (139 → 132). Default `True`, así EDA/no-supervisado quedan intactos. |
| T2 | S1,S6 | inline | hecho | `src/reduce.py`, `src/sweep.py` y `src/production.py` (supervisado) usan `include_profile=False`. El no-supervisado de `production.py` usa la matriz con `Profile.*` con su propia reducción. |
| T3 | S6 | inline | hecho | `reduccion.csv` y `barrido_ventana.csv` regenerados sin `Profile.*`; bundles `supervised*.joblib` regenerados (block_pca 36 features, base 132, reduced 10). Los no-supervisados quedaron con `Profile.*` intactos. |
| T4 | S2 | inline | hecho | Notebook 02 reescrito: fuga al inicio (sección 0), `build_matrices(include_profile=False)`, números actualizados (132 features, block_pca AUC 0,901 / espec. S0 0,507). |
| T5 | S2 | inline | hecho | Re-ejecutado end-to-end: 49/49 celdas de código, 0 errores (~708 s). |

## Log

- **L1 (usuario, textual):** "la verdad es que quiero eliminar profile o no incluirlo como lo tenemos ahora quizas incluir al principio que succede si se incluy o mejor mostrar partes de tablas que se vea claramente la fuga, se que es un cambio grande pero no le veo el sentido a dejarlo"
- **L2 (usuario, alcance):** "Supervisado completo (Recomendado)" — excluir `Profile.*` del detector supervisado de punta a punta; EDA y no-supervisado aparte.
- **L3:** Decisión de mecanismo: `build_matrices` gana `include_profile` (default `True`), no se borra ninguna columna cruda (S5).
- **L4:** Consecuencia ya medida (RF, LOSO): sin `Profile.*`, `block_pca` da AUC 0,902 y espec. S0 0,507 (contra 0,952/0,815 con perfil). `physical_corr` también usa 5 columnas `Profile.*` de 15, así que su espec. 0,996 también cambia al excluirlas.
- **L5 (hallazgo 2026-11-20):** sin `Profile.*`, la ventaja de `block_pca` casi desaparece: `corr` (50 columnas) da AUC 0,906 y recall@5% 0,610, por encima de `block_pca` (0,901 / 0,527); `block_pca` solo gana en recall@1% (0,359 vs 0,322) y en compacidad. El "block_pca gana" era en parte fuga de `Profile.*`. También: la "mejora" del rango móvil en S0 (0,466→0,948 con perfil) era fuga — sin perfil es 0,455→0,523. Se mantiene `block_pca` como receta (más compacta, mejor recall@1%), declarando que `corr` es una alternativa válida y más simple.
