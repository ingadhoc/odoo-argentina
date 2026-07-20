---
applyTo:
  - "**/models/**/*.py"
  - "**/wizards/**/*.py"
  - "**/wizard/**/*.py"
  - "**/controllers/**/*.py"
  - "**/report/**/*.py"
---

# Revisión de rendimiento (ORM)

## Anti-patrones que bloquean performance

- **Search en loop** → N+1 queries. Reemplazar por una sola `search` con dominio `in` sobre ids, o `_read_group` / `search_fetch`.
  ```python
  # MAL
  for order in orders:
      payments = self.env['payment'].search([('order_id', '=', order.id)])
  # BIEN
  payments = self.env['payment'].search([('order_id', 'in', orders.ids)])
  ```
- **Create/write/unlink en loop** → múltiples roundtrips a DB. Vectorizar:
  ```python
  # MAL
  for vals in data:
      self.env['res.partner'].create(vals)
  # BIEN (Odoo 17+)
  self.env['res.partner'].create(data)  # lista de dicts
  ```
- **`search([])` + filtrado en Python** → traer todos los records. Usar dominio preciso.
- **`mapped` en loop** sobre recordsets grandes → preferir una única `.mapped('field')` fuera del loop.

## `@api.depends` afinado

- Listar todas las dependencias **reales**, incluidas las dotted: `@api.depends('partner_id.email')` para evitar consultas extra.
- No listar campos ajenos al compute (dispara recomputes innecesarios).
- Evitar depender de campos no almacenados en cadenas largas.

## Agregados

- Para sumar/contar preferir `read_group` / `_read_group` / `formatted_read_group` (Odoo 17+) antes que iterar + `sum`/`len`.
- `search_count(domain)` en vez de `len(search(domain))`.
- `browse(ids)` en lugar de re-buscar cuando ya se tienen ids.

## Relacionales

- **N+1 por navegación**: si un `@api.depends` dispara muchas lecturas, ajustar dependencias o prefetch.
- `mapped('campo_relacional.subcampo')` agrupa lecturas y usa prefetch; preferir a loops manuales.
- `filtered_domain(domain)` para filtrados con mismo idioma que `search`.

## Cron y jobs largos

- **Odoo 19**: usar `self.env['ir.cron']._commit_progress(remaining=N)` / `_commit_progress(processed=M)` en crons en lugar de `notify_progress` / commits manuales ad hoc.
- Procesar en **lotes** (`batch_size` razonable, p. ej. 500–1000) y commitear por lote.
- Logs con `_logger.info` para observabilidad.

## Computes y store

- `store=True` sobre `compute` implica backfill en historia → ver `migrations.instructions.md`.
- `compute` sin store se reevalúa por read; si se accede repetidas veces en un loop, cachear localmente.
- `write` dentro de un compute → anti-patrón, genera recursión o recomputes encadenados.

## Transacciones

- `flush()` explícito solo cuando se requiere forzar la orden de escritura antes de leer. No usar en loops.
- `env.cr.commit()` en crons o scripts de migración, pero nunca dentro de lógica transaccional de usuario.
- `invalidate_cache` solo si hay razón concreta (modificación externa por SQL directo).

## Vistas XML relacionadas (cross-reference)

- Filtros en listas grandes sobre campos no indexados → sugerir `index=True` en el modelo.
- Columnas de lista que nunca se muestran: `column_invisible="1"` (evita cargar valores). Ver `views.instructions.md`.

## Cuándo NO optimizar

- Loops sobre recordsets pequeños y acotados (< ~20 elementos) donde la claridad gana a la micro-optimización.
- Código de setup/install que corre una única vez.
- Para diffs chicos y acotados, evitar proponer reescrituras masivas — preferir marcar la regla para futuras iteraciones.

## Beneficios indirectos

- Mantenerse dentro del ORM hereda controles de acceso, auditoría, reglas multi-compañía y prefetch automático. Queries crudas pierden todo eso.
