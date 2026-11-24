# CONCACAF validation ledger

This ledger records the evidence boundary for the integrated feature. The historical notes below are retained as development evidence. Combined FL27 validation is intentionally pending.

| Evidence class | Coverage |
| --- | --- |
| Directly validated in FL27 | Each of the four competitions was individually exercised in isolated FL27 builds before the latest integration. Champions Cup qualification and 11-tie handover, Caribbean Cup semifinal losers and bronze match, and the Central American eight-team knockout and play-in were exercised in their respective validation builds. For Leagues Cup, profile 20271146 recorded two completed 62-match editions, a full restart and career reload, refreshed 2027 participation, Champions Cup qualification and native standings, knockout and ranking screens. |
| Automated | Eight regional combinations, 16 generation cases with complete/incomplete Champions Cup, recipe migration, exact ranks and domestic cup winners, duplicate cascades, runtime parser limits, source eligibility and geographic exclusions, stable allocation, qualification UI lifecycle and presentation projections. Scheduling stress and native harnesses cover split groups/knockouts, late processing and rollback/recovery. |
| Pending in FL27 | Combined custom world built with the final integrated UI and contracts, save/load and annual rollover using the individual domestic qualification contracts, selected split-league sources, and actual native registration with split matchdays or September recovery. Late external calendar changes and fallback routes remain incompletely covered in live play. |

The first 20271146 run recorded 124 distinct Leagues Cup match IDs across two editions. Both completed with common dates. A second journey from the October 2026 save completed 2027 with the flexible group scheduler and also used common dates. Therefore neither proves split registration or September group recovery in FL27. Recorded dates and native checks support the rest requirement, but the archives do not contain a complete external calendar at the close.

The final 2026 statistics reconciled 144 credited goals with 144 match goals, excluding shootouts. The 2027 flexible-group replay reconciled 176 and recorded 98 assists across 171 contributors. Both native ranking controllers received 40 rows. The 2026 fingerprints matched across the recorded startups and the final 2027 fingerprints matched the audited totals. Those findings belong to 20271146, before the current combined contracts.

Local evidence anchors include `out/leagues-cup-full` and profile 20271135, `out/leagues-cup-native-ui/evidence-20271146/two-editions-20261124-155214182`, `player-stats-validated-20261124-163741391`, and `flexible-groups-2027-20261124-170711324/final-rankings` under the same evidence root. The [Caribbean notes](caribbean.md) and [CONCACAF integration history](concacaf.md) identify the earlier packages and known limitations.

### Combined live acceptance, deferred

Using a new isolated custom world, verify actual entrants against nonconsecutive league positions, a verified domestic cup winner and a same-league replacement. Verify both regional bronze outcomes where applicable, Champions Cup byes and Round One handover, and all Leagues Cup matches, tables and player statistics. Save and reload before and after qualification, repeat after a full restart, and cross the next annual draw. Preserve plans, fixture IDs, dated results and logs. Use an intentionally congested scenario to exercise split dates and recovery separately from the common-date case.

---

# Validación de Leagues Cup en Competition Info

El paquete `out/leagues-cup-native-ui/standings-validation-20271138` contiene las tablas nativas de MLS y Liga MX, la página conjunta de los 54 partidos de Fase Uno y las tres páginas de eliminatorias. Usa el perfil `20271138` y conserva la configuración anual y el enlace a Champions Cup. Sider carga los módulos con el overlay desactivado.

## PowerShell desde la raíz del repositorio

El perfil `20271135` tenía una transacción activa en `OneDrive\Documentos` al verificar el paquete. El primer comando condicional usa la restauración habitual del lanzador, que comprueba el inventario, conserva las partidas y el diario de esa sesión en el archivo de aislamiento y devuelve los guardados originales. Si falla, interrumpe la secuencia y conserva las rutas para diagnóstico. Cierra FL27, Sider, Mod Studio y OneDrive antes de la transición.

```powershell
$ErrorActionPreference = 'Stop'
$launcher = '.\tools\central_probe_launch.ps1'
$package = '.\out\leagues-cup-native-ui\standings-validation-20271138'
$evidence = '.\out\leagues-cup-native-ui\evidence-20271138'
$python = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\python.exe'
$profile = '20271138'
$audit = '.\tools\leagues_live_audit.ps1'
$journal = Join-Path ([Environment]::GetFolderPath('MyDocuments')) `
    "SPGAME\Football Life\$profile\save\fl26swiss-state.bin"

& $launcher -Mode Verify -Prototype $package -Profile $profile
if (Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'FL27-Central-American-isolation-20271135\active')) {
    & $launcher -Mode Restore -Profile 20271135
}
& $launcher -Mode Prepare -Prototype $package -Profile $profile
& $launcher -Mode VerifyRouting -Prototype $package -Profile $profile
& $launcher -Mode Launch -Prototype $package -Profile $profile

# Ejecuta Capture-LC con la pantalla indicada abierta. Mantén visible la pantalla hasta que termine.
function Capture-LC([string]$Label, [switch]$Complete, [string]$Baseline) {
    $options = @{}
    if (Test-Path -LiteralPath $journal) { $options.Journal = $journal }
    if ($Complete) { $options.RequireComplete = $true }
    if ($Baseline) { $options.Compare = $Baseline }
    & $audit -Package $package -Evidence $evidence -Python $python -CompetitionInfo -Label $Label @options
}
```

Cada captura genera un directorio fechado con el estado de la auditoría, las llamadas de los controladores, la selección actual, los registros y los partidos de la competición activa, los resultados calculados de Leagues Cup y el log del runtime. Guarda una captura de pantalla por etiqueta para vincular lo visible con esos datos. El colector lee el proceso por la ruta exacta del ejecutable del paquete.

## Secuencia en FL27

1. Inicia una Master League con Austin FC en 2026 y avanza hasta el sorteo de Leagues Cup a fines de julio o comienzos de agosto. Desde el menú de Master League, abre **Competition Info → Leagues Cup**. Captura el menú con `Capture-LC 'menu'` y comprueba que existe una sola entrada pública.
2. Abre **Phase One - MLS standings**. Comprueba el título y el escudo y baja hasta la fila 18. Ejecuta `Capture-LC 'mls'` con la tabla abierta. Vuelve un nivel y abre **Phase One - Liga MX standings**. Repite con `Capture-LC 'liga-mx'`. Haz otra pasada tras disputar algunos partidos para comprobar el orden y los puntos de un resultado con tanda. Los registros de inicialización deben indicar 18 filas para `700` y `701` respectivamente.
3. En **Leagues Cup → Phase One - Fixtures and Results**, recorre la página hasta el último encuentro y ejecuta `Capture-LC 'phase-one'`. Repite cuando se hayan jugado los 54 partidos. La auditoría lista los 54 encuentros con sus fechas, resultados y tandas. El log del proveedor informa cuántas entradas entregó al controlador nativo.
4. Desde **Leagues Cup**, abre **Quarterfinals**, **Semifinals** y **Final and third place** a medida que aparezcan. Ejecuta `Capture-LC 'quarterfinals'`, `Capture-LC 'semifinals'` y `Capture-LC 'final-and-third'` con cada página abierta. Tras la final, toma `Capture-LC '2026-complete' -Complete`.
5. Vuelve al selector de **Competition Info**, abre **Chile → Copa Chile → Fixtures** y comprueba que hay un cuadro visual de varias rondas. Es el control nativo de 16 clubes del paquete, CID `56` y reglamento `68`. Ejecuta `Capture-LC 'control-copa-chile'` con el cuadro abierto y guarda una imagen en la que se distingan los cruces. Si la carrera no ofrece ese cuadro, busca **España → Copa del Rey → Fixtures** como control alternativo, CID `17` y reglamento `25`, y usa `Capture-LC 'control-copa-del-rey'`. La captura comparativa debe mostrar ramas del cuadro, así como los registros y partidos de la competición de control.
6. Guarda la carrera, cierra FL27 y Sider y vuelve a ejecutar **VerifyRouting** y **Launch** desde la misma sesión de PowerShell. Carga la partida y abre de nuevo la página de resultados. Usa `Capture-LC '2026-reload' -Complete -Baseline '<ruta al fixtures.json de 2026-complete>'`. Si se avanza a 2027, repite las tablas y los fixtures tras el sorteo y guarda la evidencia de las plazas de enero en Champions Cup y del cuadro de 2027.

La auditoría conserva capturas parciales si FL27 rechaza la página o si la comprobación deportiva posterior detecta una diferencia. Anota la etiqueta y el último elemento visible, y conserva el directorio de esa captura.
## Validación de dos ediciones en el perfil 20271146

El paquete `out/leagues-cup-native-ui/flexible-calendar-validation-20271146` se validó en una misma carrera. Las pruebas cubrieron las dos tablas nativas de 18 clubes, la lista nativa de eliminatorias, los marcadores y penales y el reinicio completo del juego con recarga de la carrera. Las tablas de 2027 empezaron a cero.

| Edición | Partidos | Final | Tercer puesto |
| --- | ---: | --- | --- |
| 2026 | 62 | Atlas 2–2 Charlotte FC, 7–6 en penales | Club América 1–1 Real Salt Lake, 7–6 en penales |
| 2027 | 62 | Atlético San Luis 4–1 Nashville SC | Querétaro 4–2 Minnesota United |

Las fechas reales coincidieron con las reservas en ambas ediciones. La fase de grupos se disputó el 6, 12 y 20 de agosto, los cuartos el 31 de agosto, las semifinales el 10 de septiembre y la final y el tercer puesto el 23 de septiembre. La auditoría encontró 124 IDs distintos y un mínimo de seis días entre partidos de Leagues Cup de un mismo club. Pasaron las comprobaciones nativas de descanso. La evidencia archivada no contiene un volcado completo del calendario externo al cierre.

Los 18 clasificados MLS para 2027 coincidieron con los primeros 18 de la tabla doméstica 2026 de 30 clubes. Los otros 18 coincidieron con la membresía registrada de Liga MX. El diario persistente conservó los dos podios. En la Champions Cup 2027, Atlas entró directamente a octavos, Charlotte FC y Club América entraron en primera ronda y el sorteo conservó 27 participantes únicos. El registro confirma los 22 partidos preliminares completados, el avance de los 11 ganadores, los 29 encuentros inscritos del cuadro principal y Atlético San Luis como campeón.

El resumen con ambos calendarios, los 27 participantes de Champions Cup, sus registros y los hashes se conservó en `out/leagues-cup-native-ui/evidence-20271146/two-editions-20261124-155214182/`. Los guardados y paquetes de validación son artefactos locales.

### Límites del calendario

Las dos ediciones encontraron fechas comunes. La inscripción nativa de una ronda dividida y la recuperación ante un cambio tardío de calendario están cubiertas offline y quedan pendientes de validación en vivo. En los mismos 1.500 calendarios de estrés, el planificador flexible admitió 786 ediciones y completó 764 en simulación. El planificador de fechas comunes había admitido 766 y completado 744. Los calendarios sin fecha compatible para una pareja, con capacidad insuficiente o con cambios que agotan las alternativas siguen bloqueándose. La recuperación se acota al 31 de octubre y las fechas de partidos ya inscritos se conservan. Los generadores continentales y las rutas domésticas de último recurso pueden introducir conflictos después de reservar.

## Fuente de goles y asistencias

El constructor nativo de rankings de FL27 lee el registro `rec596` de cada partido antes de ordenar y recortar la tabla. En `0x140fbd667` recorre las dos alineaciones de hasta 17 jugadores desde `rec596+0x24`, con filas de `0x10` bytes. Dentro de cada fila, `+4` identifica al jugador, `+8` contiene sus goles y `+9` sus asistencias. Los penales de la tanda están en los campos de marcador de equipo y no forman parte de esos totales.

El lector de Leagues Cup reconstruye ambos rankings al abrir Competition Info. Lee los partidos completados de la edición activa y sus réplicas, usa el ID completo de partido y consolida por ID estable de jugador antes del corte nativo de 40 filas. La vista no escribe tablas deportivas ni crea archivos de persistencia.

Las rutas nativas de guardado y carga llaman a `0x140b05450` desde `0x141401df9` y `0x141401848`. El bucle en `0x140b05563` copia los 34 registros de jugador. La evidencia archivada de 20271146 acredita la recarga de la carrera y la finalización de ambas ediciones, pero no incluye una captura de esas filas antes y después de reiniciar. La igualdad de los rankings reconstruidos en FL27 queda pendiente de esa comparación.

La validación del guardado de octubre registró 62 partidos, 145 jugadores con contribuciones, 144 goles y 71 asistencias. Ambas proyecciones tenían 40 filas, mientras que la interfaz mostraba 13 goleadores y siete asistentes. El constructor de la lista nativa en `0x140b175f0` usa en `0x140b1768b` un selector diferente, `0x14157c5d0`, que recibe el reglamento, la etapa y el tipo de ranking. Copia las filas según el contador de la tabla devuelta y entrega el tamaño del vector al control de lista. La corrección se aplica a esa llamada para Leagues Cup y registra el número de filas y el máximo de la tabla parcial y de la edición. `scoreboard_goals` suma los goles de partido y prórroga, y `uncredited` registra la diferencia con los goles individuales sin atribuirla automáticamente a autogoles.

La prueba posterior con el mismo guardado de 2026 confirmó que el controlador recibió 40 goleadores y 40 asistentes, con máximos de seis y tres. La lectura nativa por reglamento habría entregado 13 y siete, ambos con máximo de dos. Los 62 marcadores sumaron 144 goles sin tandas, todos acreditados a jugadores. Las huellas `b5cdba71047a7eb8` (goles) y `0baace0705cd8232` (asistencias) coincidieron entre los dos arranques. La regresión de menú verifica que las dos entradas de estadísticas preceden a Reglas y que Reglas es la última entrada.

## Calendario de grupos por partido

La ruta conjunta mantiene las jornadas comunes cuando el plan habitual funciona. Si falla, asigna los mismos 54 cruces a sus réplicas nativas, con un calendario por pareja que considera la capacidad, las fechas desconocidas y los bloqueos de los dos clubes. Comprueba tres días de descanso y exige una reserva común de eliminatorias o una contingencia para todos los posibles clasificados antes de iniciar la inscripción. La recuperación usa como máximo el 30 de septiembre para grupos y el 31 de octubre para eliminatorias. La búsqueda tiene un presupuesto de 2.000 nodos por ventana.

La inscripción verifica las 54 fechas y las listas nativas del calendario antes de confirmar. La reversión cubre la edición completa y una reversión sin verificar mantiene el bloqueo de seguridad. Al recargar, los 54 registros nativos reconstruyen las fechas exactas de las réplicas. El diario conserva los máximos de cada lote y las reservas de eliminatorias en su formato existente. Las máscaras por partido registran días desconocidos, capacidad, conflictos externos y, cuando hay un plan, descanso frente a las otras fechas asignadas.

La reconstrucción sintética de los dominios `3/2/3/2/3/2` prueba tanto una solución con lotes divididos en agosto como otra con inicio de planificación el 21 de agosto y partidos en septiembre. El log de esa carrera de 2027 solo conserva dominios agrupados. No demuestra que los cruces concretos tengan una solución en el calendario real. En los 1.500 escenarios, se planificaron 1.172 ediciones y se completaron 1.149, frente a 786 y 764 con el planificador anterior. La inscripción dividida y la recarga están comprobadas en el banco nativo de pruebas y requieren validación en FL27.

### Prueba posterior desde el guardado de octubre de 2026

El nuevo recorrido de 20271146 seleccionó los primeros 18 de la clasificación anual MLS de 2026 y los 18 miembros de Liga MX. Completó 62 partidos con IDs únicos. Los grupos se disputaron el 6, 12 y 20 de agosto de 2027, y las eliminatorias el 31 de agosto, 10 y 23 de septiembre. Las fechas reales coincidieron con las reservas. El descanso mínimo entre encuentros de Leagues Cup fue de seis días. El log acredita la comprobación del calendario externo al inscribir los grupos y la auditoría nativa de las eliminatorias. No hay una captura completa del calendario externo al cierre.

El plan de esta carrera funcionó con jornadas comunes, sin lotes ni rondas divididas y sin usar la ventana de recuperación. Por tanto, el recorrido valida la compatibilidad del planificador nuevo con la inscripción común y la progresión anual. La ruta dividida sigue cubierta por las pruebas offline. El diario con checksum válido conserva el podio de CD Guadalajara, Pachuca CF y CD Necaxa. Guadalajara ganó la final 1–0 y Necaxa ganó el tercer puesto 1–0 a CD Atlas.

Las estadísticas empezaron en cero. Los marcadores sumaron 157 goles en grupos y 19 en eliminatorias. Los 176 goles, excluidas las tandas, coinciden con el total acreditado a los jugadores. El agregado registró 98 asistencias, 171 jugadores con contribuciones y dos tablas de 40 filas. La evidencia local se conserva en `out/leagues-cup-native-ui/evidence-20271146/flexible-groups-2027-20261124-170711324/`.

Al abrir las dos pantallas nativas después de la final, el controlador recibió las 40 filas de goleadores (máximo de seis, huella `122b9479f3c61304`) y las 40 de asistencias (máximo de cuatro, huella `4f5aa80892a1171c`). Las dos huellas coincidieron con la auditoría previa de los 62 partidos. La confirmación se archivó en el subdirectorio `final-rankings`. No se ejercitaron en vivo la inscripción de lotes divididos ni la recuperación de grupos en septiembre, que siguen validadas únicamente offline.
