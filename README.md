# Conciliador Tarjetas Maveric Sevens 0.4.2

Nueva interfaz Azul Sevens: encabezado celeste claro, cargas compactas y simétricas, títulos y logos centrados y GENERAR CONCILIACIÓN. Barra lateral común: logo de Tarjetas, abrir carpeta, equipo, versión/fecha y cerrar. Logo oficial de Sevens al pie.

El motor, los mapas de tarjetas y las autorizaciones se conservan idénticos a la instalación 0.3.6 de la Mac. Actualmente se concilia Brex; Visa/Mastercard requieren sus propios lectores antes de ofrecerlos como opciones.

## Resultados

Se guardan automáticamente en Documentos/Conciliador Tarjetas/Archivos conciliados/Brex/AAAA-MM-DD/. La carpeta corresponde al día de ejecución. El nombre incluye el período detectado en Brex y la fecha y hora de generación, con fracción de segundo para evitar sobrescrituras.

Windows resuelve la carpeta Documentos del sistema, incluida su redirección a OneDrive. Los históricos anteriores siguen en su ubicación original; no se mueven ni se eliminan. El botón Abrir carpeta de conciliaciones abre la nueva carpeta de resultados.

## Instalación y actualización

El programa mantiene su carpeta App Conciliador Tarjetas Maveric/Archivos APP y el acceso de escritorio con su logo. Los usuarios no necesitan Git, GitHub ni un Python instalado manualmente. El lanzador descarga el entorno privado si falta, comprueba dependencias y busca actualizaciones al abrir. Sin conexión continúa con la versión instalada. El puerto habitual de Tarjetas sigue siendo 8783.

Los instaladores Mac y Windows están incluidos. Windows crea el acceso con icono en el escritorio real del usuario; Mac conserva el nombre y el icono de la aplicación del escritorio. Solo se reemplazan archivos del programa, con respaldo y recuperación ante fallos. Se conservan resultados, configuración local ajena al programa y runtimes.

## Desarrollo local

Este directorio es un repositorio Git conectado a stournier77/Conciliador-tarjetas-Sevens. Rama de pruebas: design/tarjetas-sevens-0.4.2. Se incorpora el código fuente al repositorio; los archivos financieros, runtimes, históricos, logs y respaldos no se incluyen.

Abrir_Prueba_Mac.command abre esta versión en el puerto temporal 18783, sin actualizar ni reemplazar la instalación habitual. Una vez validado el diseño, publicar la versión estable con los paquetes latest_mac.zip, latest_pc.zip y version.txt para que los equipos se actualicen al abrir su acceso habitual.

## Validación

Ejecutar python -m unittest discover -s tests -p 'test_*.py'. Se comprueban rutas y nombres, conciliación de una operación de prueba, separación por empresa, interfaz, conservación de históricos, validación de paquetes y recuperación del actualizador. Los tres chequeos originales del motor están en tests/test_engine.py.

Mac comprobada con el entorno de la aplicación instalada. La prueba de ejecución nativa en un PC sigue pendiente; preparar un paquete Windows no sustituye esa comprobación.

La prueba reinicia solamente su propia instancia del puerto 18783 y espera a que responda antes de abrir el navegador. La recarga de cambios queda habilitada para evitar mostrar una interfaz anterior.

## Publicación desde GitHub

La rama de diseño ejecuta pruebas en Mac y Windows. Al integrar una nueva versión en main, GitHub Actions genera y valida los paquetes y publica el Release con latest_mac.zip, latest_pc.zip y version.txt. Incrementar app/config.py y version.txt antes de cada publicación. El código fuente queda disponible para mantenerlo desde los chats de cada aplicación.

El panel izquierdo abre expandido y el control para ocultarlo se deshabilita para evitar perder el acceso a las acciones.

## Corrección de reapertura en Windows (0.4.2)

El lanzador usa primero el Python válido del entorno instalado. La búsqueda de Python administrado captura stdout, stderr y el código de salida sin que PowerShell 5.1 interrumpa el flujo al informar un intérprete ausente; si hace falta lo instala automáticamente. Si el programa sigue abierto, el acceso vuelve a abrir su ventana. La reconstrucción del entorno usa el intérprete base antes de renombrar la venv anterior.

Para equipos cuyo lanzador anterior no llega a comprobar actualizaciones, ejecutar una vez Reparar_Inicio_Tarjetas_PC.bat. Descarga el paquete oficial, verifica SHA256, respalda y reemplaza únicamente el lanzador de Windows y su auxiliar; después abre el acceso y deja que actualice el resto del programa. No modifica conciliaciones ni resultados.
