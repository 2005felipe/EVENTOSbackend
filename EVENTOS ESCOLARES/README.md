# Backend — Eventos Escolares

Guía de instalación y lectura del backend FastAPI que expone la API escolar y conecta con PostgreSQL en Neon.

## Qué contiene

```text
EVENTOS ESCOLARES/
├── app/
│   ├── api/routes/       # Endpoints HTTP de FastAPI
│   ├── core/             # Conexión a PostgreSQL, hashing y seguridad JWT
│   ├── models/           # Validación de datos de entrada y salida
│   ├── repositories/     # Consultas y escrituras SQL
│   └── static/           # Recursos estáticos servidos por la API
├── database/migrations/  # Cambios SQL incrementales de la base de datos
├── .env                  # Configuración local y secretos; no se comparte
├── .venv/                # Entorno Python local; no se comparte
├── main.py               # Crea FastAPI, configura CORS y registra routers
├── asignar_clave_general.py
└── requirements.txt      # Dependencias de Python
```

## Preparar y ejecutar localmente

Desde esta carpeta, en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

La API local escucha por defecto en `http://127.0.0.1:8000`. La documentación interactiva de FastAPI queda en `http://127.0.0.1:8000/docs`; `/redoc` muestra la documentación alternativa. La raíz `/` devuelve un mensaje de estado. El endpoint `/favicon.ico` sirve `app/static/favicon.ico`.

El archivo `.venv` es un entorno aislado creado por Python. Contiene el intérprete/enlaces locales y los paquetes instalados para este proyecto, por ejemplo FastAPI, psycopg2, PyJWT y pwdlib. No contiene la base Neon ni es el código fuente. Se puede volver a crear con los comandos anteriores y está excluido por `.gitignore`; no se debe enviar ni copiar entre computadoras.

## Configuración local

`main.py`, `app/core/database.py`, `app/core/security.py` y el script de clave cargan variables desde `.env`. No incluyas ese archivo en Git, ZIP compartidos, capturas o documentación.

El backend de base de datos lee estas variables:

| Variable | Uso |
|---|---|
| `DB_HOST` | Host PostgreSQL de Neon |
| `DB_NAME` | Nombre de la base |
| `DB_USER` | Usuario PostgreSQL |
| `DB_PASSWORD` | Contraseña PostgreSQL |
| `DB_PORT` | Puerto; el código usa `5432` si no se define |
| `JWT_SECRET_KEY` | Secreto para firmar y validar tokens; mínimo 32 caracteres |
| `JWT_ACCESS_MINUTES` | Duración del token; por defecto 30 minutos |
| `CORS_ORIGINS` | Orígenes frontend separados por coma; opcional en desarrollo |

### Neon: obtener y configurar la conexión

Neon aloja la base de datos PostgreSQL del sistema. En el panel del proyecto de Neon, abre **Connect** y selecciona la rama y base que usa la aplicación. De los datos de conexión toma el host, nombre de base, usuario, contraseña y puerto, y colócalos en las variables `DB_*` del `.env` local del backend. No copies la cadena completa de conexión en el frontend ni la publiques.

El archivo `.env` va en la carpeta raíz del backend, al mismo nivel que `main.py`. Puedes crearlo con esta plantilla y reemplazar los valores entre `< >` localmente:

```dotenv
DB_HOST=<host-de-neon>
DB_NAME=<nombre-de-base>
DB_USER=<usuario-postgresql>
DB_PASSWORD=<contrasena-postgresql>
DB_PORT=5432
JWT_SECRET_KEY=<secreto-aleatorio-de-al-menos-32-caracteres>
JWT_ACCESS_MINUTES=30
CORS_ORIGINS=http://localhost:5173
```

`DB_HOST` contiene solo el hostname PostgreSQL que Neon muestra (por ejemplo, un nombre que empieza por `ep-` y termina en `.neon.tech`), sin `postgresql://`, sin usuario/contraseña y sin `/nombre-base`. Esos componentes van por separado en `DB_USER`, `DB_PASSWORD` y `DB_NAME`. En Neon selecciona **Connect**, la rama, compute, base y rol PostgreSQL correctos. Para este cliente `DB_PORT` normalmente es `5432`; SSL y `channel_binding=require` se pasan desde `database.py`, no se pegan como query string.

Para crear un secreto JWT aleatorio desde la terminal, ejecuta `python -c "import secrets; print(secrets.token_urlsafe(48))"` y pega el resultado solo en el `.env` local. En desarrollo se puede omitir `CORS_ORIGINS`, porque `main.py` permite localhost en el puerto 5173 por defecto. La conexión PostgreSQL exige SSL. Neon también entrega `DATABASE_URL`/`DATABASE_URL_UNPOOLED`, pero la aplicación actual no las consume; requiere los campos `DB_*` indicados arriba.

El `.env` usado por FastAPI contiene una credencial técnica que puede leer o modificar los datos según sus privilegios. El usuario PostgreSQL y el acceso a la consola/SQL Editor de Neon son distintos del login escolar; conocer `DB_PASSWORD` no equivale a iniciar sesión como administrador del portal. En producción, limita los privilegios de la credencial de aplicación a las tablas y operaciones que necesita, separa desarrollo de producción y no incluyas valores reales en Git, capturas o README.

`app/core/database.py` abre la conexión con `sslmode="require"` y `channel_binding="require"`, aplica un timeout y entrega filas como diccionarios (`RealDictCursor`).

#### Qué significa conectar con Neon en este sistema

El recorrido de los datos es **frontend → FastAPI → PostgreSQL en Neon**. El navegador no usa un SDK de Neon ni recibe credenciales de base de datos. FastAPI usa `psycopg2`; los repositorios abren una conexión, ejecutan SQL parametrizado y la cierran. No se usa un ORM ni un pool de conexiones de aplicación en el código actual.

En Neon hay varios conceptos que no se deben confundir:

| Concepto | Uso en este proyecto |
|---|---|
| Proyecto y rama (branch) | Contienen un entorno de PostgreSQL. Cada rama puede tener datos distintos y su propia conexión; revisa que el `.env` apunte al entorno correcto antes de cambiar datos o correr una migración. |
| Compute/endpoint | Proporciona el host PostgreSQL al que se conecta la API. El host `DB_HOST` debe corresponder a la rama y endpoint seleccionados en **Connect**. |
| Usuario PostgreSQL (`DB_USER`) | Credencial técnica con la que FastAPI abre la base. No es la cuenta de una persona del portal. |
| Usuario del portal (`usuario`) | Registro de la aplicación con correo, hash de contraseña, `rol_id` y estado. La API valida esta fila para iniciar sesión. |
| Rol PostgreSQL vs. rol del portal (`rol`) | El rol PostgreSQL habilita acceso a la base; `rol` define perfiles de negocio como estudiante, docente o administrador. Son identidades y permisos separados. |

Neon también ofrece un endpoint con pooler, identificado en el host con `-pooler`. Puede ayudar a aplicaciones con muchas conexiones concurrentes. La API actual crea y cierra conexiones por operación; no administra un pool propio. Si se decide utilizar el endpoint pooled, configura exactamente el host que entrega Neon en `DB_HOST` y valida el comportamiento con la versión de `psycopg2` y la opción `channel_binding` de esta app. La documentación oficial explica cómo [obtener los datos de conexión](https://neon.com/docs/connect/connect-from-any-app), los [computes](https://neon.com/docs/manage/computes) y el [pool de conexiones](https://neon.com/docs/connect/connection-pooling).

La carpeta `database/migrations/` no sincroniza automáticamente el código con Neon. El esquema debe existir primero; luego se aplican las migraciones disponibles en orden, en la rama correcta y después de un respaldo. Las migraciones son SQL de cambios, no un mecanismo de autenticación ni un reemplazo de copias de seguridad. Neon permite crear ramas para trabajar en entornos separados; consulta su guía de [ramas de base de datos](https://neon.com/docs/get-started/workflow-primer).

`CORS_ORIGINS` debe contener el origen exacto del sitio Svelte en producción, por ejemplo el esquema y host, sin rutas. Si está vacío, `main.py` permite los orígenes de desarrollo `http://localhost:5173` y `http://127.0.0.1:5173`. CORS es una regla que aplica el navegador para permitir que el frontend lea respuestas de otro origen; no reemplaza el login ni la autorización.

## Arquitectura y archivos importantes

### `main.py`

Es el punto de entrada `uvicorn main:app`. Carga `.env`, instancia `FastAPI`, prepara CORS y registra todos los routers. En `app.include_router(...)` se ve la relación entre cada grupo de rutas y sus dependencias de permisos. Los routers de autenticación, estudiantes, acudientes, inscripciones, autorizaciones, asistencias y notificaciones aplican controles dentro de sus endpoints; usuarios, roles, módulos, categorías, actividades y asociaciones docente-actividad también reciben controles al incluirse desde aquí.

El orden importa cuando una ruta general como `/{id}` podría coincidir con rutas específicas como `/resumen`; los routers definen sus rutas concretas y FastAPI genera el esquema OpenAPI que se consulta en `/docs`.

### `app/core/`

- **`database.py`**: única fábrica de conexiones PostgreSQL. Lee las variables `DB_*`, valida que estén presentes, habilita TLS requerido y crea conexiones `psycopg2` con `RealDictCursor`. Los repositorios abren y cierran conexiones usando esta clase.
- **`passwords.py`**: crea hashes Argon2 con `pwdlib.PasswordHash.recommended()` y compara una contraseña presentada con un hash. `verificar_password` falla de forma cerrada ante hashes vacíos o malformados; si la verificación resulta válida y el algoritmo recomienda actualizar el hash, devuelve el hash nuevo.
- **`security.py`**: contiene la autenticación compartida por la API. Firma tokens JWT HS256, valida su emisor, firma y vencimiento, vuelve a leer el usuario/rol desde Neon, verifica que estén activos y ofrece `exigir_modulo(...)` para autorización por rol/módulo. También coordina la verificación de contraseña durante login.
- **`__init__.py`**: marca `core` como paquete Python; no inicia la API.

### `app/api/routes/`

Cada archivo crea un `APIRouter` y declara operaciones HTTP (`GET`, `POST`, `PUT`, `DELETE`). El router recibe y valida el cuerpo con modelos Pydantic, llama a un repositorio y convierte errores de negocio o ausencia de datos en respuestas HTTP. Los prefijos registrados actualmente son:

| Archivo | Prefijo | Responsabilidad principal |
|---|---|---|
| `auth_routes.py` | `/auth` | Lista de roles para el login, login y perfil actual (`/me`). |
| `rol_routes.py` | `/roles` | Consulta y administración de roles. |
| `usuario_routes.py` | `/usuarios` | Cuentas, filtro/resumen y creación de fichas de estudiante o acudiente según rol. |
| `modulo_routes.py` | `/modulos` | Catálogo de módulos del portal. |
| `modulo_rol_routes.py` | `/modulos-roles` | Matriz de módulos habilitados por rol. |
| `estudiante_routes.py` | `/estudiantes` | Expedientes de estudiantes, resumen y vínculos con acudientes. |
| `acudiente_routes.py` | `/acudientes` | Expedientes de acudientes, resumen y vínculos con estudiantes. |
| `categoria_actividad_routes.py` | `/categorias-actividades` | Catálogo de categorías. |
| `actividad_routes.py` | `/actividades` | Actividades, consultas, resumen y relaciones de participantes/docentes. |
| `actividad_docente_routes.py` | `/actividades-docentes` | Asignaciones, docentes disponibles y disponibilidad por actividad/docente. |
| `inscripcion_routes.py` | `/inscripciones` | Inscripciones, resúmenes y operaciones propias de estudiante/acudiente. |
| `autorizacion_routes.py` | `/autorizaciones` | Autorizaciones asociadas a inscripciones y acudientes. |
| `asistencia_routes.py` | `/asistencias` | Asistencia, nota y retroalimentación asociadas a una inscripción. |
| `notificacion_routes.py` | `/notificaciones` | Avisos, destinatarios y estado de lectura. |
| `audit_response.py` | — | Ayuda a responder después de una operación con datos de auditoría del registro. |
| `__init__.py` | — | Hace disponibles los módulos de rutas que importa `main.py`. |

Los nombres y permisos de los módulos en la base deben coincidir con los que consulta `exigir_modulo`. Las reglas de seguridad del servidor son las definitivas: ocultar un botón en Svelte no protege por sí solo una operación.

## Ciclo de una solicitud FastAPI

FastAPI recibe una solicitud HTTP y la procesa en estas etapas:

1. **Origen y middleware:** el servidor ASGI/Uvicorn entrega la solicitud a `app` de `main.py`. `CORSMiddleware` indica al navegador si el origen del frontend puede leer la respuesta. CORS no impide que otro cliente HTTP intente llamar a la API y no identifica a la persona.
2. **Enrutamiento:** FastAPI busca el método y ruta registrados (`GET /estudiantes`, `POST /auth/login`, etc.) en los routers incluidos desde `main.py`. Si no hay ruta, responde `404`.
3. **Validación:** el cuerpo, parámetros de ruta y query se validan contra el modelo Pydantic y las anotaciones del endpoint. Datos inválidos producen `422` antes de ejecutar la operación.
4. **Dependencias:** `Depends(...)` ejecuta requisitos compartidos. En rutas privadas, obtiene y valida el Bearer JWT, consulta la cuenta/rol vigente y revisa el módulo/acción requerida. El login y listado de roles son públicos para que una persona pueda iniciar sesión.
5. **Reglas de negocio:** la función del router comprueba reglas propias del recurso; por ejemplo, que el rol destino exista o que el acudiente esté vinculado con el estudiante solicitado.
6. **Persistencia:** el router delega al repositorio. El repositorio ejecuta SQL PostgreSQL con parámetros separados, confirma (`COMMIT`) la operación exitosa o revierte (`ROLLBACK`) si hay un error y cierra la conexión.
7. **Respuesta:** FastAPI convierte el resultado a JSON (y aplica `response_model` cuando existe), con código HTTP correspondiente. Los errores esperados usan `HTTPException`; los no controlados aparecen como error de servidor y se registran en la terminal de Uvicorn.

La capa de rutas no debe recibir credenciales de base ni construir SQL dinámico con datos concatenados. Los modelos Pydantic validan la forma del dato; no sustituyen autorización, restricciones de base o reglas de negocio. `/docs` muestra el OpenAPI generado y permite probar endpoints, pero los protegidos requieren token. El comando `uvicorn main:app --reload` es para desarrollo; en despliegue se configura un servidor ASGI y HTTPS en el entorno de hosting.

### `app/models/`

Estos modelos Pydantic describen y validan los datos que acepta o devuelve la API; no crean tablas. Por ejemplo, validan longitudes, tipos booleanos, campos opcionales, rangos numéricos y modelos específicos para vínculos. `base.py` configura los cuerpos para ignorar marcas `creado`/`actualizado` que el cliente pudiera mandar, porque PostgreSQL es quien las administra. `auth.py` valida correo, contraseña y rol del login. `usuario.py` separa creación, actualización y respuesta pública; `UsuarioPublic` omite deliberadamente `password`.

Los demás modelos corresponden a los recursos escolares: `actividad`, `actividad_docente`, `acudiente`, `asistencia`, `autorizacion`, `categoria_actividad`, `estudiante`, `inscripcion`, `modulo`, `modulo_rol`, `notificacion` y `rol`. `__init__.py` agrupa exports del paquete.

### `app/repositories/`

Esta capa concentra el SQL y la comunicación directa con PostgreSQL. Las rutas no deberían construir consultas SQL: delegan a repositorios para listar, buscar, insertar, actualizar, desactivar, resumir o asociar registros. Hay repositorios por recurso y repositorios de autenticación/permisos. Las operaciones que cambian varios datos (por ejemplo, crear usuario y su ficha de estudiante/acudiente) deben usar transacciones para no dejar registros parciales. `__init__.py` organiza el paquete.

### `database/migrations/`

Las migraciones son cambios incrementales de esquema/datos que se aplican manualmente a Neon, una sola vez y en orden numérico. **No se ejecutan al iniciar FastAPI** y no reemplazan un respaldo. Las migraciones actuales (000 a 014; las que siguen son las incrementales):

1. `001_auditoria_automatica.sql`: crea la función/trigger que gestiona `creado` y `actualizado` en las tablas existentes.
2. `002_estado_booleano.sql`: convierte los estados históricos a `BOOLEAN`, normaliza nulos y establece valores predeterminados/`NOT NULL`.
3. `003_inscripcion_nota_retroalimentacion.sql`: añade temporalmente evaluación a inscripción con nota limitada a 0–5.
4. `004_evaluacion_en_asistencia.sql`: traslada nota y retroalimentación a asistencia, conserva datos previos y permite asistencia desconocida (`NULL`).
5. `005_creador_notificacion.sql`: agrega la referencia al usuario que creó la notificación e índice.
6. `006_permisos_roles_escolares.sql`: ajusta asociaciones de módulos y permisos de perfiles escolares.
7. `007_alcance_director.sql`: restringe para dirección la consulta nominal de algunos módulos operativos, conservando resúmenes.
8. `008_modulos_parcial_2.sql`: desactiva módulos/pantallas auxiliares que ya no corresponden al portal; conserva historia.
9. `009_notificaciones_por_usuario.sql`: habilita el módulo de notificaciones para consulta individual.
10. `010_consulta_autorizacion_estudiante.sql`: habilita la consulta de autorización propia para estudiante, con filtrado en API.
11. `011_vinculo_acudiente_estudiante.sql`: crea la tabla de relación permanente acudiente-estudiante y conserva relaciones derivadas de autorizaciones existentes.
12. `012_asistencia_acudientes.sql`: habilita a acudientes a consultar asistencia de estudiantes asociados.
13. `013_matriz_final_roles.sql`: deja la matriz final de permisos por rol.
14. `014_correo_unico_sin_mayusculas.sql`: normaliza los correos a minúscula y crea un índice único sin distinguir mayúsculas. Si hay correos repetidos solo avisa (NOTICE); corrígelos y vuelve a ejecutarla.

Estas migraciones presuponen que ya existe el esquema principal (tablas y columnas base). Esta carpeta contiene cambios incrementales, no un script inicial completo para crear una base vacía. Antes de aplicar una migración en una base con datos, revisa su SQL y respalda Neon.

## Contraseña compartida y Argon2

La columna `usuario.password` guarda **un hash Argon2**, no la contraseña legible. La API realiza el hash con `app/core/passwords.py` antes de insertar o actualizar. Neon guarda literalmente ese resultado codificado; Neon no crea el hash ni puede recuperar el texto original. Argon2 está diseñado para que, al iniciar sesión, se pueda verificar una contraseña candidata sin poder descifrar la guardada.

`asignar_clave_general.py` es una utilidad administrativa puntual para las cuentas que ya existen:

1. Carga `.env` y pide la nueva contraseña dos veces mediante `getpass` (no la muestra al teclear).
2. Rechaza la operación si no coincide o si tiene menos de 8 o más de 128 caracteres.
3. Conecta a Neon y bloquea/lee las filas de `usuario` dentro de una transacción.
4. Exige escribir exactamente `RESTABLECER TODAS` antes de continuar.
5. Genera un hash Argon2 para cada fila y actualiza su columna `password`; confirma todo con `COMMIT` o revierte con `ROLLBACK` ante cancelación/error.

La contraseña introducida es igual para todas las cuentas existentes tras ejecutar el script. Como Argon2 usa sal, cada fila puede guardar un hash diferente aunque todas acepten la misma contraseña. El script **no muestra, guarda en un archivo ni permite volver a consultar** la contraseña después. Tampoco es un proceso automático de usuarios futuros: `usuario_routes.py` exige la contraseña al crear la cuenta y la procesa con `hash_password`; el script debe volver a ejecutarse para restablecer cuentas existentes.

Ejecutarlo es una acción amplia y afecta todas las cuentas: activa `.venv`, revisa que `.env` apunte a la base correcta, respalda la base y ejecuta `python asignar_clave_general.py` solo cuando se desea realmente restablecerlas todas. No se puede deshacer el cambio sin conocer las claves anteriores (que no se conservan en texto).

## JWT: sesión y autorización

1. Svelte consulta `GET /auth/roles` para llenar el selector de perfil.
2. Envía `POST /auth/login` con correo, contraseña escrita y `rol_id`.
3. La API busca la cuenta por correo y rol, comprueba estados y verifica el texto recibido contra el hash Argon2.
4. Si es válido, `auth_routes.py` responde `access_token`, `token_type` y el perfil (`usuario`, `rol`, `modulos`).
5. `security.py` firma un JWT con HS256 y claims `sub` (id de usuario), `rol_id`, `iat`, `exp` e `iss`. El token dura `JWT_ACCESS_MINUTES` (30 minutos por defecto).
6. El frontend envía `Authorization: Bearer <token>` en llamadas siguientes. `obtener_usuario_actual` verifica firma, algoritmo, emisor, vigencia, existencia/estado de cuenta y rol actual en Neon.
7. `exigir_modulo(...)` comprueba módulos activos y, según endpoint/método, rol permitido. En cambios de permisos, el control real ocurre en la API.
8. `GET /auth/me` vuelve a obtener el perfil y los módulos autorizados. Un `401` lleva al frontend a cerrar sesión.

El JWT está **firmado, no cifrado**: no pongas contraseñas ni secretos en sus claims. `JWT_SECRET_KEY` debe ser secreta, fuerte, diferente en cada entorno y no cambiarse accidentalmente, porque tokens firmados con la clave vieja dejarían de validar. El acceso se invalida al vencer o si la API detecta que el usuario/rol está inactivo/no coincide; los permisos de módulo se vuelven a consultar desde la base.

### Qué ocurre al autenticar una cuenta registrada

La autenticación responde a **quién eres**; la autorización decide **qué puedes hacer**. En este proyecto la base de Neon es la fuente de verdad para ambas cosas. Elegir “Docente” en el formulario no convierte una cuenta en docente: la API comprueba que el `rol_id` enviado pertenece a la cuenta encontrada por correo.

1. `GET /auth/roles` es público y devuelve solo roles activos de la tabla `rol`. El frontend usa esos IDs para llenar el selector.
2. `POST /auth/login` recibe JSON con `correo`, `password` y `rol_id`. `LoginRequest` normaliza el correo a minúsculas y espacios recortados, valida tipos y límites, y rechaza entradas inválidas con `422`.
3. `AuthRepository.buscar_usuario_para_login` busca el correo normalizado y exige que coincida el rol elegido. La consulta es parametrizada; la contraseña no se agrega al SQL.
4. `autenticar_credenciales` exige que usuario y rol estén activos y compara la contraseña presentada con `usuario.password` mediante Argon2. Una cuenta inexistente, inactiva, un rol incorrecto y una contraseña incorrecta reciben el mismo `401` para no revelar cuál dato falló.
5. Si `pwdlib` recomienda fortalecer un hash antiguo, la API lo actualiza después de una verificación correcta. No se reemplaza el hash antes de comprobar la contraseña.
6. `obtener_perfil` consulta el usuario, su rol y los módulos habilitados en `modulo_rol` + `modulo`. Si no hay módulos activos, el login responde `403` y no emite un token.
7. `crear_token_acceso` firma el JWT con HS256. La respuesta contiene `access_token`, `token_type: bearer` y el perfil público. Nunca devuelve el hash de la contraseña.
8. Para cada endpoint protegido, `HTTPBearer` extrae el token y `obtener_usuario_actual` exige los claims, verifica firma, algoritmo permitido, emisor y expiración; luego vuelve a consultar Neon y comprueba que usuario y rol sigan activos y que el `rol_id` vigente sea el del token.
9. `exigir_modulo(...)` y las dependencias de routers deciden si ese rol tiene el módulo y permiso para ese recurso y método. Algunos endpoints también comprueban propiedad o vínculo (por ejemplo, estudiante o acudiente). Estas comprobaciones se hacen en la API, aunque el frontend oculte enlaces y botones.

El `401` significa que faltan credenciales, son inválidas o vencieron; el frontend borra la sesión y vuelve al login. El `403` significa que la identidad fue reconocida, pero no tiene permiso para el recurso/acción, o que el perfil autenticado carece de módulos activos. Un `422` normalmente indica que el cuerpo no cumple el contrato Pydantic. Las rutas de consulta y login pueden explorarse en `/docs`; los endpoints protegidos se autorizan desde Swagger con `Authorization: Bearer <token>`.

### Qué autenticación implementa y qué alternativas hay

El código actual implementa un **login propio de la aplicación que emite access tokens JWT Bearer**. No implementa un proveedor OAuth2/OpenID Connect: `/auth/login` recibe JSON (`correo`, `password`, `rol_id`), y `security.py` usa `HTTPBearer` para leer el token. Por tanto, es correcto describirlo como autenticación JWT con cuentas locales de Neon, pero no como un flujo OAuth2 Password ni como Neon Auth.

Para este portal de primera parte, mantener usuarios y roles en las tablas actuales y comprobarlos en la API sirve al requisito de aceptar solo cuentas registradas con un perfil autorizado. JWT no da permisos por sí solo: en esta app la API consulta el rol y los módulos desde Neon y aplica reglas por endpoint. Si el requisito cambia a inicio de sesión único, Google/Microsoft u otro proveedor de identidad, la alternativa recomendada es OpenID Connect con Authorization Code y PKCE; no se debe crear un nuevo flujo OAuth de usuario y contraseña. El estándar de seguridad OAuth actual prohíbe el grant de contraseña para nuevos diseños ([RFC 9700, sección 2.4](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4)); la guía de [FastAPI sobre JWT y hash de contraseñas](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) muestra herramientas relacionadas, pero el login de este repositorio tiene su propio contrato.

Para una aplicación web de producción con requisitos más estrictos, también se puede usar una sesión opaca administrada por el servidor y una cookie `HttpOnly; Secure; SameSite`, o un patrón BFF. Esto facilita invalidar sesiones inmediatamente y evita que JavaScript lea el token. El diseño requiere cambiar coordinadamente FastAPI, CORS/CSRF y frontend; no es una opción activada por el README. OWASP advierte que `sessionStorage` y `localStorage` son accesibles a JavaScript y recomienda no guardar allí credenciales de sesión ([Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)).

#### Alcance y límites de los JWT actuales

- Son access tokens de 30 minutos por defecto; el código no emite refresh tokens ni mantiene una lista de revocación por token.
- Cerrar sesión elimina el JWT del navegador, pero no invalida una copia robada. La copia sigue siendo utilizable hasta expirar, salvo que la cuenta/rol se desactive, cambie el rol asociado o rote `JWT_SECRET_KEY`.
- Un cambio de contraseña por sí solo no revoca de inmediato JWT ya emitidos. Para invalidación inmediata se necesita versión de sesión, lista de revocación o sesiones guardadas en servidor.
- Un JWT firmado no es cifrado: el payload se puede leer. No agregues contraseña, secretos ni información sensible. PyJWT documenta que el algoritmo permitido debe fijarse en el servidor al decodificar ([API de PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html)); esta app fija `HS256`.
- La seguridad del transporte requiere HTTPS en producción. En desarrollo, el tráfico a `127.0.0.1` es local y HTTP.
- El login no incorpora límite de intentos, demora progresiva, bloqueo temporal ni MFA. Además, para una cuenta inexistente la verificación Argon2 no corre; aunque el mensaje `401` sea genérico, un atacante podría intentar inferir cuentas por diferencias de tiempo. Para una publicación real, agrega limitación de intentos, monitoreo y considera verificar un hash ficticio cuando no exista el correo. Revisa las medidas de [OWASP para autenticación](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
- La API de login valida contraseña de hasta 128 caracteres y la creación de usuarios exige entre 8 y 128. Estos límites no son sustituto de reglas de longitud, recuperación de cuenta ni protección frente a intentos automatizados.

## Dependencias y archivos de soporte

- `requirements.txt`: versiones fijadas de FastAPI/Uvicorn, psycopg2, Pydantic, python-dotenv, PyJWT y `pwdlib[argon2]`.
- `.gitignore`: excluye `.env`, `.venv`, bytecode, cachés y logs.
- `.env`: configuración local; mantener fuera de Git y de los paquetes que se envían.
- `app/static/favicon.ico`: icono que sirve `main.py`.

## Diagnóstico rápido

- **Error de variables PostgreSQL:** verifica `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y opcionalmente `DB_PORT`; no basta con `DATABASE_URL` en el código actual.
- **Falla CORS en navegador:** agrega el origen exacto del frontend a `CORS_ORIGINS`, reinicia Uvicorn y comprueba que la URL de API del frontend apunta al servidor correcto.
- **401:** correo/contraseña/rol no coinciden, el hash almacenado no verifica, el token expiró o la cuenta/rol está inactivo.
- **403:** sesión válida, pero no hay permiso activo para ese módulo/acción.
- **500 al consultar tablas/columnas:** compara Neon con el esquema esperado y revisa si faltan migraciones aplicadas en orden.


## Seguridad: cambios recientes

- **Límite de intentos de login:** 5 fallos por IP+correo en 15 minutos devuelven `429` con `Retry-After`. Se ajusta con `LOGIN_MAX_INTENTOS` y `LOGIN_VENTANA_SEGUNDOS`. El conteo es en memoria y por proceso.
- **Último administrador:** la API rechaza desactivar o cambiar de rol al último administrador activo, y a un administrador que intente hacerlo sobre su propia cuenta.
- **Errores de base de datos:** duplicados, referencias inválidas y datos fuera de rango responden `409`/`400` con mensaje claro en lugar de `500`.
- **Secretos:** si el `.env` se compartió (por ejemplo dentro de un ZIP), rota la contraseña de Neon y `JWT_SECRET_KEY`.
