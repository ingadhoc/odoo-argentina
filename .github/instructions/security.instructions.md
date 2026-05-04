---
applyTo:
  - "**/security/**"
  - "**/controllers/**/*.py"
  - "**/models/**/*.py"
  - "**/wizards/**/*.py"
  - "**/wizard/**/*.py"
---

# Revisión de seguridad

## ACL y reglas de acceso

- Modelo nuevo debe tener fila en `security/ir.model.access.csv` con permisos **mínimos necesarios**. No abrir `perm_unlink` o `perm_write` si no se justifica.
- Campos sensibles (datos personales, flags de configuración, credenciales) deben restringirse por `groups="..."`.
- `record rules` (`ir.rule`) nuevas deben cubrir multi-compañía cuando el modelo tiene `company_id`. Verificar reglas globales vs por grupo.
- **Odoo 19**: `res.groups.category_id` fue reemplazado por `privilege_id` + `res.groups.privilege`; al crear grupos usar la nueva estructura.

## SQL injection

- **Bloqueante**: `self.env.cr.execute("... '%s' ..." % var)` o con f-string/`.format`. Toda variable debe pasar como parámetro:
  ```python
  self.env.cr.execute("SELECT id FROM res_partner WHERE name = %s", (name,))
  ```
- Preferir dominio ORM: `self.env['res.partner'].search([('name', '=', name)])`.
- **Odoo 19**: usar clase `SQL` con `execute_query_dict()` para consultas seguras; marcar si se ve `cr.execute` crudo.

## Ejecución arbitraria y deserialización

- `eval()`, `exec()`: nunca sobre input del usuario.
- Dominios construidos como string y pasados por `eval` → bloqueante. Usar lista de tuplas o `Domain(...)`.
- `safe_eval` permitido solo sobre contextos controlados; marcar si viene de parámetros de request.
- `pickle.loads`, `yaml.load` (sin `SafeLoader`), `marshal`: prohibidos con data no confiable.

## Bypass de reglas

- `sudo()` en controllers/wizards: cada uso requiere justificación explícita. Evitar `sudo()` amplio a nivel de método.
- `with_user(SUPERUSER_ID)` sólo para operaciones de sistema documentadas.
- Accesos multi-compañía sin `company_id` explícito: riesgo de leakage; exigir scoping.

## Controllers HTTP

- `auth='public'` con escritura o acceso a datos sensibles → riesgo. Evaluar si debería ser `auth='user'` o `auth='portal'`.
- `@http.route(..., csrf=False)` solo para endpoints no-UI (webhooks, APIs) y con autenticación alternativa; marcar si se desactiva sin justificación.
- `browse(int(request.params.get('id')))`: validar pertenencia del registro al usuario actual antes de operar.
- Input del usuario que llega a SQL, filesystem o shell → ver secciones específicas.

## Filesystem y comandos

- `subprocess.*` con `shell=True` → bloqueante. Pasar args como lista.
- Paths construidos con input del usuario sin validar → path traversal. Usar `werkzeug.utils.secure_filename` o equivalente.
- URLs descargadas con input del usuario → riesgo SSRF; validar esquema y host permitido.

## Sensibles específicas Odoo 19

- Integraciones IA, VOIP, WhatsApp, Equity/ESG: cambios acá pueden requerir migración de tokens/ownership. Revisar con atención y sugerir script si aplica (ver `migrations.instructions.md`).

## Criterio de severidad

- **Bloqueante** (BLOCKER): SQL injection, eval sobre input, shell=True, deserialización insegura, `auth='public'` con efectos secundarios graves.
- **Alto** (HIGH): `sudo()` sin justificación, bypass de ACL, record rules faltantes.
- **Medio** (MEDIUM): falta `groups` en campos sensibles, `noupdate` sin considerar consecuencias.
