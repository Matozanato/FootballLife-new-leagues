# FL Mod Studio 0.4.0 — inicio rápido (FL26 y FL27)

> [English](../en/quick-start-0.4.0.md) · [hrvatski](../hr/quick-start-0.4.0.md) · **español** · [português](../pt/quick-start-0.4.0.md) · [français](../fr/quick-start-0.4.0.md)

Todo lo que necesitas para empezar con 0.4.0, en orden. Cada página y opción a fondo está en la
[guía de uso](mod-studio-guide.md); un zip de mundo listo está en [Instalar un paquete listo](install-a-pack.md).
¿Vienes de 0.2.5.1 o anterior? Lee también el [inicio rápido de 0.3.0](quick-start-0.3.0.md).

## 1. Antes de actualizar

- **Guarda una copia de tu carpeta de partidas guardadas y de tu carpeta vieja de Mod Studio**,
  como siempre.
- **Después de actualizar, instala otra vez los módulos: 1. Inicio → Instalar ahora.** Muchos
  arreglos están en nuestros módulos dentro del juego.
- **Una carrera en curso se queda con lo que tiene su partida guardada.** Las ligas, copas y clubes
  nuevos de un mundo actualizado llegan solo en una Master League nueva. Tu carrera sigue con las
  ligas que tiene.
- **Licencia nueva.** Desde 0.4.0 Mod Studio está bajo la FL Mod Studio License (`LICENSE.txt` en
  el zip). Sigue siendo libre de usar, cambiar y compartir. No se permite venderlo ni quitar la
  marca "Powered by FL ModStudio". 0.3.0 y las anteriores siguen bajo la licencia MIT.

## 2. Consigue 0.4.0

**Tienes 0.3.0:** **Ayuda → Buscar actualizaciones...** → **Descargar e instalar**. Mod Studio se
cierra, pone los archivos nuevos en su carpeta y se abre otra vez.

**Primera vez, o a mano:** descarga `FL26ModStudio-0.4.0.zip` de la
[última versión](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) y
descomprímelo en una carpeta propia (por ejemplo `Documents\FL26 Mod Studio`). No lo ejecutes
desde dentro del zip, y deja `_internal` y `pack` junto a `FL26ModStudio.exe`. Haz doble clic en
`FL26ModStudio.exe`. Si Windows dice "Windows protegió su PC": **Más información** → **Ejecutar
de todas formas**. Tus ajustes, mundos y recetas están en `%APPDATA%\FL26ModStudio`, así que se
quedan.

**Elige el juego:** **5. Ajustes → Examinar...** → la carpeta con `FL_2026.exe` (FL26) o
`FL_2027.exe` (FL27), no `SiderAddons` → **Usar esta carpeta**. La primera vez, Mod Studio
descomprime las tablas del juego: un minuto o dos, espera.

## 3. Tu mundo de 0.3.0

1. **1. Inicio → Instalar ahora** (los módulos de 0.4.0).
2. Un mundo que construyes tú: **2. Mi mundo → Construir e instalar** una vez. Muchos arreglos de
   0.4.0 necesitan un Build nuevo.
3. Carga tu carrera y sigue jugando. Las ligas, copas y clubes nuevos llegan solo en una Master
   League nueva.

Un mundo listo de un zip (GigaPack, un Modpack) no necesita Build. Cuando su autor te da una
versión nueva, instala el zip nuevo igual que la primera vez (sección 4).

## 4. GigaPack (Football Life 2027)

GigaPack by MatoZanato 1.0 es un mundo listo para **Football Life 2027**: 317 ligas y 5.239
clubes, en un solo zip, que instala Mod Studio, sin Build. Descargas, md5, lo que todavía no puede
hacer y los problemas conocidos: [GigaPack](../../docs/gigapack.md) (en inglés).

En resumen (necesitas FL27 con la **actualización 1.1**; antes cierra el juego y su launcher):

1. Mod Studio 0.4.0, y la carpeta del juego con `FL_2027.exe` (sección 2).
2. No descomprimas GigaPack. **1. Inicio → Importar un zip de mundo** → elige `GigaPack-1.0.zip` →
   **Instalar el mundo**. Espera a **Listo para jugar**. Si dice **Casi listo**, lista lo que hay
   que arreglar.
3. El botón verde **Iniciar el juego** en Mod Studio (o el launcher de FL27, no `FL_2027.exe`
   directamente) → **Master League** → **New game**. Solo una Master League nueva recibe las
   ligas nuevas.

## 5. Novedades de 0.4.0 y dónde encontrarlas

| Qué | Dónde |
|---|---|
| GigaPack 1.0, un mundo listo de 317 ligas para FL27 | [GigaPack](../../docs/gigapack.md) (sección 4) |
| Un zip de mundo entra de una vez | **2. Mi mundo → + Añadir... → Elegir un archivo...** → el zip → **Instalar el mundo** |
| Importa tu mundo dice si un zip es una versión más nueva, más antigua o la misma de tu mundo | **1. Inicio → Importar un zip de mundo** |
| Una actualización de un mundo que compartes mantiene las carreras de sus jugadores: Exportar pide una versión | **Exportar...** en la tarjeta del mundo en **2. Mi mundo**; FAQ (en inglés): [Updating a shared world without breaking careers](../../docs/faq.md#updating-a-shared-world-without-breaking-careers) |
| Una pestaña para las copas: copas nacionales y competiciones continentales | **2. Mi mundo → Copas**: **Países del juego**, **Nuestros países**, **Continental**. **Aplicar**, luego **Construir e instalar** |
| Trofeos, también en FL27 (en FL27 todavía no comprobado en el juego) | **3. Contenido del juego → Trofeos** |
| Una tercera copa para las divisiones inferiores (FL27) | **Ligas → Editar liga... → Tercera copa (como el EFL Trophy)**, tus propias fechas en **Fechas de copa** |
| Ligas de hasta 32 clubes (de 29 a 32 se enfrentan una vez); FL27 acepta también 8 y 9. Todavía no jugadas una temporada entera en el juego | **Ligas → Editar liga... → Clubes** |
| Tu propio orden de los clubes de una liga en Select Team (FL27) | **2. Mi mundo → Clubes → Más → Orden en Select Team...** |
| Un botón **Guardar** para un jugador | **2. Mi mundo → Jugadores**, junto a **Deshacer los cambios de este jugador** |
| FL27: ids de competición hasta 1023 (FL26 se queda en 255) | **COMPETICIONES** arriba en **2. Mi mundo**, después de **1. Inicio → Instalar ahora** |
| Animaciones, y cómo apagarlas | **5. Ajustes → Programa → Animaciones (las páginas, los botones y los diálogos aparecen suavemente)** |

Todo lo demás, con los arreglos: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) (en inglés).

## 6. ¿Algo va mal?

1. **4. Herramientas → Diagnóstico → Hacer las comprobaciones → Copiar un informe.**
2. En nuestro [Discord](https://discord.gg/StQqtk3G3M): **#support** → **Open a support ticket** en
   el mensaje fijado, con el informe, una captura de pantalla, `sider.log` y `sider.ini` (el menú
   **Juego** abre los dos).

Conocido en 0.4.0: [problemas conocidos](../../docs/known-issues.md#open-in-mod-studio-040-2026-11-21) ·
qué cambió: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) ·
preguntas frecuentes: [FAQ](../../docs/faq.md)
