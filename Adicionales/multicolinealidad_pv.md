# Multicolinealidad en Columnas de Perfil Fotovoltaico (`Profile.pv_*`)

En el dataset Data4Cyber, las siguientes variables del bloque `Profile.` presentan relaciones físicas y algebraicas directas que producen multicolinealidad casi perfecta ($r^2 > 0.999$):

1. **`Profile.pv_reactive_kvar` a partir de `Profile.pv_active_kw`**:
   - El perfil modela el inversor operando con factor de potencia constante ($\cos\phi \approx 0.90$).
   - Por física de CA:
     $$Q \approx -0.484 \times P$$
   - Correlación: $r \approx -0.9998$ ($r^2 > 0.9995$).
   - Una es prácticamente un múltiplo lineal de la otra.

2. **`Profile.pv_active_kw` a partir de `Profile.pv_input_kw`**:
   - Representa la potencia activa de salida en CA calculada a partir de la entrada en CC, afectada por el rendimiento del inversor:
     $$P_{\text{active}} \approx 0.982 \times P_{\text{input}}$$
   - Correlación: $r \approx 0.9999$ ($r^2 > 0.9999$).

---

### Criterio para Selección de Atributos (Feature Selection)
Para evitar problemas de redundancia y distorsión en modelos sensibles a la colinealidad (como regresiones lineales/logísticas, distancias en K-Means o pesos en SVM):
- Conservar una sola de las tres (típicamente `Profile.pv_active_kw`).
- Descartar `Profile.pv_input_kw` y `Profile.pv_reactive_kvar` sin pérdida de información útil.
