---
applyTo:
  - "**/migrations/**/*.py"
  - "**/__manifest__.py"
  - "**/models/**/*.py"
---

# Revisión de scripts de migración

> Si el diff introduce cambio estructural en un modelo, **siempre** evaluar si corresponde proponer script en `migrations/<version>/`.

## Cuándo proponer script

1. **Rename de campo almacenado** (`Char`, `Many2one`, etc. o `compute` con `store=True`). **No** si es `compute` sin store.
2. **Rename de modelo**: siempre. Toca `ir.model`, `ir.model.data`, tablas relacionales, vistas, acciones.
3. **Cambio de tipo de campo** con cambio real en DB (`Char→Many2one`, `Selection→Many2one`, `Many2one→Many2many`). Cambios compatibles (`Char→Text`, ajustes de `Float`) no requieren script.
4. **Split/merge de campos**.
5. **Nuevo `compute` con `store=True`** que aplique a registros históricos → post-script de backfill en lotes. Advertir si el modelo tiene millones de registros.
6. **Cambio en keys de `selection`**: renombrar/eliminar existentes → script que mapee `old → new`. Agregar nuevas keys **no** requiere script.
7. **Cambio de dominio** en relacional que excluya valores usados históricamente → limpiar/remapear.
8. **Nueva `UNIQUE`/índice** (`_sql_constraints` o `models.Constraint`): pre-script que resuelva duplicados antes de crear la constraint.
9. **Cambios en `ir.model.data` / XML IDs** (rename `module.name → module2.name2`): script para actualizar referencias.
10. **Registros con `noupdate="1"`** cuyo contenido lógico cambia: forzar update por `xml_id`.
11. **Cambios en reglas de acceso / multi-company / multi-website**: rellenar campos obligatorios, recomputar ownership.

> **No** proponer script solo por `required=True` nuevo sin default, salvo que el diff evidencie datos históricos incompatibles.

## Pre / Post / End

- **pre**: antes del update. Preparar datos/esquemas para evitar fallos.
- **post**: después. Recalcular, limpiar, ajustar referencias.
- **end**: al final del upgrade global. Tareas cross-módulo o finales.

Regla: **rompe durante el upgrade → pre**; **recalcula después → post**; **global al final → end**.

## Mapeo cambio → acción

- **Rename campo almacenado** → pre: copiar datos viejo→nuevo. Post: cleanup + recomputes.
- **Rename modelo** → pre: mapear `ir.model`/`ir.model.data`. Post: re-enlazar vistas, acciones, menús, reglas.
- **Split/merge** → pre: copiar a nuevos campos antes de que el schema borre el viejo. Post: normalizar/recompute.
- **`compute` nuevo con `store=True`** → post: backfill en lotes (pre opcional en modelos grandes para preparar columna).
- **Cambio de tipo con conversión** → pre: columna temporal + conversión. Post: swap/rename/borrar vieja.
- **`selection` (remove/rename keys)** → pre: mapeo `old → new` (usar `change_field_selection_values` si aplica). Post: validar consistencia.
- **Nueva `UNIQUE`** → pre: resolver duplicados. Post: crear índice si aplica.
- **`noupdate="1"` con cambio lógico** → post: update por `xml_id`.

## Convenciones

- Ubicación: `migrations/<module_version>/` (ej. `migrations/19.0.1.0/`). Versión debe coincidir con `__manifest__.py`.
- Nombres: `pre_<desc>.py`, `post_<desc>.py`, `end_<desc>.py`.
- **Idempotentes**: seguros ante re-ejecución.
- **En lotes** (`batch_size` razonable) para datasets grandes.
- Logs claros (`_logger.info`); comentario al inicio documentando supuestos y garantías.
- Evitar transacciones muy largas; `env.cr.commit()` controlado o helpers de progreso.

## Versión del manifest

- Al introducir cambio estructural, **bumpear** versión en `__manifest__.py` para que el script corra (ej. `19.0.1.0 → 19.0.2.0`).
- La carpeta bajo `migrations/` debe coincidir con la nueva versión.
