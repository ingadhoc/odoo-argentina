# Instrucciones para Copilot – Revisión de código Odoo

## Contexto

Este repositorio contiene módulos Odoo. La versión objetivo está declarada en `__manifest__.py` de cada módulo. Las reglas específicas por dominio viven en `.github/instructions/*.instructions.md`, cada una con `applyTo:` que delimita a qué archivos aplica.

## Reglas globales (aplican a todo cambio)

1. **Responder siempre en español.**
2. Feedback **breve, concreto y accionable**. Lista corta de 3–7 puntos. Evitar párrafos largos y no repetir lo que ya dice la descripción del PR.
3. Corregir errores de tipeo u ortografía evidentes en nombres y comentarios (cuando sean claros).
4. No proponer traducciones de docstrings/comentarios entre idiomas.
5. No exigir docstrings en métodos que no los tienen. Si ya existe uno, PEP8 alcanza; falta de tipos o `return` **no es un error**.
6. No proponer cambios puramente estéticos (espacios, comillas, orden de imports).
7. Traducciones: `_()` y `self.env._()` son indistintos; solo marcar mensajes/textos al usuario que no estén envueltos.

## Resumen operativo

- **Si hay cambio estructural** (rename de campos almacenados, cambio de tipo, split/merge, nuevos `compute` con `store=True` con backfill, cambio de keys de `selection`, nuevas `UNIQUE`, cambios en `ir.model.data`/XML IDs) → **proponer script de migración** en `migrations/<version>/` con enfoque idempotente y en lotes. Ver `migrations.instructions.md`.
- **Si hay cambio en modelos** → aplicar `models.instructions.md`.
- **Si hay cambio en vistas XML** → `views.instructions.md`.
- **Si hay cambio en seguridad / ACL / `cr.execute` / `eval`** → `security.instructions.md`.
- **Si cambia `__manifest__.py`** → `manifest.instructions.md`.
- **Si el diff es grande y sensible a performance** → `performance.instructions.md`.
- **Si introduce funcionalidad no trivial sin tests** → `tests.instructions.md`.
- **Si hay texto al usuario sin `_()`** → `i18n.instructions.md`.

## Versionado Odoo

Cada módulo declara versión en `__manifest__.py`. Cuando hay diferencias relevantes entre v18 y v19, los archivos en `instructions/` marcan la regla como "Odoo 19+" o "Odoo 18".

Cambios clave de Odoo 19 a tener en cuenta (detalle en cada `instructions.md` específica):
- `_sql_constraints` → `models.Constraint`, `models.Index`, `models.UniqueIndex`.
- `@api.one`/`@api.multi` eliminados; `@api.ondelete` para validación de borrado.
- `<tree>` → `<list>`; `attrs={...}` → atributos directos (`invisible=`, `readonly=`).
- `t-esc` deprecado → `t-out`.
- `cr.execute(...)` crudo desaconsejado → clase `SQL` con `execute_query_dict()`.
- Dominios con clase `Domain` y operadores `&`, `|`, `~` sobre instancias.
- Crons: `_commit_progress(remaining=, processed=)` en lugar de `notify_progress`.
- `category_id` de `res.groups` → `privilege_id` + `res.groups.privilege`.

## Estilo del feedback

- Formato recomendado: `**categoría** · descripción concreta · sugerencia`.
- Un comentario por issue; no duplicar la misma observación en varios archivos.
- Preferir mencionar la regla concreta (ej. "queries parametrizadas") antes que la teoría.
- **Checklist rápida**:

| Categoría | Qué comprobar |
|---|---|
| Modelos | Relaciones con `comodel_name`/`ondelete`; `@api.depends` correcto; `super()` preservado |
| Vistas XML | Herencias con `xpath` acotado; campos existentes; nada de redefinir vistas enteras |
| Seguridad | ACL mínimo; sin `cr.execute` con interpolación; sin `eval()` sobre input externo |
| Migraciones | Cambios estructurales → script idempotente en lotes |
| Rendimiento | Sin `search`/`write`/`create` en loop; `mapped`/`filtered`/`search_count`/`_read_group` |
| i18n | Textos al usuario envueltos en `_()`; no marcar nombres técnicos ni claves de dict |
