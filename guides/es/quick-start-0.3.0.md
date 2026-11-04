# FL Mod Studio 0.3.0 — inicio rápido (FL26 y FL27)

> [English](../en/quick-start-0.3.0.md) · [hrvatski](../hr/quick-start-0.3.0.md) · **español** · [português](../pt/quick-start-0.3.0.md) · [français](../fr/quick-start-0.3.0.md)

Todo lo que necesitas para empezar con 0.3.0, en orden. Cada página y opción a fondo está en la
[guía de uso](mod-studio-guide.md); un mundo listo o un zip de Modpack está en [Instalar un paquete listo](install-a-pack.md).

> [!WARNING]
> **0.3.0 es más bien una versión de prueba.** Si 0.2.5.1 te funciona y no necesitas FL27, no hay
> prisa: quédate en ella hasta que 0.3.0 se haya jugado un tiempo. Si llevas una carrera larga,
> guarda una copia de tu carpeta de partidas guardadas y de tu carpeta vieja de Mod Studio antes
> de actualizar.

## 1. Consigue 0.3.0

**Tienes 0.2.5.1:** **Ayuda → Buscar actualizaciones...** → **Descargar e instalar**. O cierra Mod
Studio y descomprime `FL26ModStudio-0.3.0.zip` sobre la carpeta vieja (reemplazar todo). Tus
ajustes, mundos y recetas se quedan.

**Primera vez:** descarga `FL26ModStudio-0.3.0.zip` de la
[última versión](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest),
descomprímelo en una carpeta propia (deja `_internal` y `pack` junto al exe) y ejecuta
`FL26ModStudio.exe`. Si Windows dice "Windows protegió su PC": **Más información** → **Ejecutar
de todas formas**.

La ventana ahora dice **FL Mod Studio**: es el mismo programa, con otro nombre porque también
funciona con FL27. El exe, la carpeta del zip y `%APPDATA%\FL26ModStudio` mantienen sus nombres.

## 2. Elige el juego: FL26 o FL27

1. **5. Ajustes → Carpeta del juego → Examinar...** → la carpeta con `FL_2026.exe` (FL26) o
   `FL_2027.exe` (FL27) → **Usar esta carpeta**.
2. La primera vez que eliges un juego, Mod Studio descomprime las tablas de ese juego (un minuto
   o dos; la barra de abajo lo dice). FL26 y FL27 tienen sus propias tablas y sus propias partidas
   guardadas, así que puedes cambiar de uno a otro: elige la carpeta del otro juego de la misma
   manera.
3. **1. Inicio**: cuando la comprobación previa dice que faltan los módulos o que son más viejos,
   pulsa **Instalar ahora**.

## 3. Tu mundo de 0.2.5.1 (FL26)

Tus mundos siguen funcionando. Después de actualizar:

1. **1. Inicio → Instalar ahora** (los módulos de 0.3.0).
2. **2. Mi mundo → Construir e instalar** una vez.
3. Carga tu carrera y sigue jugando. Algunos arreglos solo se ven en una Master League nueva: el
   dinero para fichajes de los clubes pequeños, las plantillas de NewLife y las ligas en los
   lugares 76, 77 y 80 de Select Team.

## 4. Clubes reales: NewLife Database 1.6b4

Descarga NewLife 1.6b4 del canal **#newlife** de nuestro [Discord](https://discord.gg/StQqtk3G3M).
**En FL27 usa 1.6b4** (o 1.6b3): las versiones anteriores se hicieron para los clubes de FL26.

1. Pon las partes (`NewLife-1.6b4-Europe.zip` ...) en una carpeta nueva, sin mezclarlas con
   otras más viejas. No descomprimas las partes.
2. **2. Mi mundo → NewLife Database → Abrir NewLife Database...** → esa carpeta.
3. **Ligas nuevas:** selecciona una o varias → **Agregar a tu mundo**. Una liga de un país en el
   que el juego ya tiene una liga (Greek Super League 2, Scottish Championship ...) entra como la
   división bajo la liga del juego, con ascensos y descensos; la página dice cuál.
4. **Ligas que agregaste de un NewLife anterior:** **Más → Actualizar mis ligas a esta versión**.
5. **Las ligas del propio juego** se quedan como el juego las tiene. **Más → Llevar las ligas del
   juego a esta temporada...** pasa sus clubes y plantillas a la temporada de NewLife, si lo
   quieres. Marca **Solo los jugadores del juego** para tener solo los traspasos y las
   valoraciones, sin jugadores nuevos.
6. **Construir e instalar**, y luego empieza una Master League **nueva**: una partida guardada
   vieja no recoge las plantillas nuevas.

## 5. Crea tu propio mundo

El camino completo, clic a clic: [Crear tus propias ligas y paquetes](make-your-own-leagues.md). En
resumen:

1. **2. Mi mundo → Ligas**: agrega una liga (o ligas de NewLife, paso 4), pon su país, clubes,
   **División**, plazas europeas y copas con **Editar liga...**.
2. **División** ahora también puede ser una de las ligas divididas del juego (Scottish
   Premiership, 3F Superliga, Jupiler Pro League): tu liga va debajo de ella con ascensos y
   descensos.
3. **Construir e instalar**, y luego una Master League nueva.

## 6. Juega

- **Iniciar el juego** (arriba a la derecha) inicia el juego con todo en su sitio.
- **FL27: inícialo siempre con su launcher** (**FL 2027 start.exe**, su acceso directo, o
  **Iniciar el juego** en Mod Studio). FL_2027.exe iniciado por sí solo puede cerrarse mientras
  se crea una Master League nueva o en sus primeros días.
- En FL27 la Champions League y la Europa League son las de FL27; Mod Studio decide quién entra
  desde tus ligas y juega las previas de verano; la Conference League es de Mod Studio.

## 7. Novedades de 0.3.0 y dónde encontrarlas

| Qué | Dónde |
|---|---|
| Soporte de FL27 | **5. Ajustes → Carpeta del juego** |
| Los clubes de una liga (con escudos) en Select Team | en el juego: Team Info, League mode ... con el cursor sobre una liga |
| Plazas con color en las tablas de las ligas (Champions League, Europa League, Conference League, ascenso, play-off, descenso) | en el juego, después de **Construir e instalar** |
| Una liga en lugar de uno de los grupos "Other ..." del juego en Select Team | **2. Mi mundo → Ligas → Lugares en Select Team** (cada liga: *Automático* o *en lugar de* un grupo), luego Build |
| Una liga bajo las ligas divididas del juego | **Ligas → Editar liga... → División** |
| Liga de NewLife bajo la liga del juego de su país | automático al **Agregar a tu mundo**; cámbialo en **División** |
| Ligas de enero a diciembre de un país nuevo: ascensos y descensos en Año Nuevo, y su copa | automático después del Build |

## 8. ¿Algo va mal?

1. **4. Herramientas → Diagnóstico → Hacer las comprobaciones → Copiar un informe.**
2. Publícalo en **#support** en el [Discord](https://discord.gg/StQqtk3G3M) (un hilo por problema)
   con una captura de pantalla y `SiderAddons\sider.log` (el menú **Juego** lo abre).

Conocido en 0.3.0: [changelog](../../docs/changelog/changelog-0.3.0.md#known) ·
preguntas frecuentes: [FAQ](../../docs/faq.md)
