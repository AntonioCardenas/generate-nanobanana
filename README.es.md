# generate-nanobanana

*Leer en otros idiomas: [English](README.md), [Español](README.es.md).*

> Skill para la generación de imágenes y videos con IA usando Google Gemini (Nano Banana 2 Lite, Nano Banana Pro, Gemini Omni Flash). Compatible con **Antigravity**, **Gemini CLI**, **Claude Code**, **Cursor** y otros entornos de agentes. Control de costos antes de ejecuciones de pago, imágenes de referencia reales y un registro de prompts al lado de cada archivo.

Un solo comando que genera imágenes y videos a través de los modelos de medios de Gemini de Google, que nunca te sorprende con una factura inesperada y archiva cada resultado —con el prompt exacto que lo generó— en una sola carpeta.

Tú dices "genera una miniatura de X". La skill redirige el trabajo al modelo correcto (borrador económico, versión final de calidad o video), carga tus imágenes de referencia reales en lugar de describir tu logotipo con palabras, te da una cotización del costo y espera tu aprobación antes de ejecutar cualquier tarea costosa, guarda el resultado directamente en una sola carpeta y escribe una pequeña nota JSON al lado que registra el prompt, el modelo y el costo. Tres semanas después, cuando miras un archivo y piensas "¿qué prompt generó ESTO?", la respuesta estará allí mismo, justo al lado.

Diseñado exclusivamente para Google: una sola clave de API, una sola factura y las características más recientes de Gemini (fusión de múltiples imágenes de Nano Banana Pro, audio sincronizado de Omni Flash) el mismo día de su lanzamiento — sin intermediarios.

[![Ejemplo de Póster Y2K Nano Banana](nanobanana_y2k_poster.png)](nanobanana_y2k_poster.png)
*Ejemplo de resultado generado con Nano Banana Pro: estética de póster Y2K.*


## Modelos

| Tarea | Modelo | ID del Modelo | Costo Estimado |
|---|---|---|---|
| Imagen (borrador) | Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | $0.03–0.05 / imagen |
| Imagen (calidad) | Nano Banana Pro | `gemini-3-pro-image-preview` | $0.13–0.30 / imagen |
| Video | Gemini Omni Flash | `gemini-omni-flash-preview` | facturado por segundo — cotizado previamente |

Cada modelo tiene su propio archivo de receta en `models/` que contiene la estructura exacta de la solicitud, el manejo de respuestas y las consideraciones especiales. Cuando Google lanza un mejor modelo, simplemente agregas un archivo markdown y la skill lo aprende. Nada más cambia.

## Instalación y Agentes Compatibles

Requisitos: una [clave de API de Google AI Studio](https://aistudio.google.com/apikey) (o la integración de la herramienta integrada sin clave de **Antigravity**), y **Antigravity**, **Gemini CLI**, **Claude Code** o cualquier otro agente que lea archivos de skill.

Instala directamente usando [`npx`](https://docs.npmjs.com/cli/v7/commands/npx) mediante el [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add AntonioCardenas/generate-nanobanana
export GEMINI_API_KEY=your_key_here   # o agrégalo a tu perfil de shell
```

Esto utiliza `npx` con el [skills CLI](https://github.com/vercel-labs/skills), que resuelve `owner/repo` directamente a este repositorio y coloca la skill en el directorio de configuración de tu agente. Es compatible con **Antigravity**, **Gemini CLI**, **Claude Code**, **Cursor**, **Codex**, **OpenCode** y otros — selecciona tu objetivo con `-a claude-code` o `-a gemini-cli`, o agrega `-g` para instalar de forma global en lugar del proyecto actual.

Si prefieres hacerlo manualmente:

```bash
git clone https://github.com/AntonioCardenas/generate-nanobanana ~/tools/generate-nanobanana
mkdir -p ~/.claude/skills
cp -R ~/tools/generate-nanobanana ~/.claude/skills/generate
```

**Reinicia tu sesión del agente en cualquiera de los dos casos.** El detector de cambios de archivos solo cubre los directorios que existían cuando comenzó la sesión, por lo que una skill instalada a mitad de la sesión no se detectará hasta que reinicies. Si parece que la skill no existe, esta es la razón.

Luego simplemente pregunta:

```
/generate a 16:9 thumbnail for my Angular signals article, use refs/logo.png
```

El repositorio se llama `generate-nanobanana` para que sea fácil de encontrar; la skill en sí se llama `generate`, por lo que el comando se mantiene corto.

## Cómo fluye una generación

1. **Ruteo (Route)** — selecciona el modelo para el trabajo y lee su archivo de receta antes de realizar cualquier llamada.
2. **Carga de referencias (Load references)** — carga logotipos, rostros y capturas de estilo reales desde `generations/refs/`. Un logotipo descrito con palabras suele salir mal; los píxeles reales no fallan.
3. **Generación (Generate)** — llama a la API de Gemini según la receta. Las imágenes responden en una sola llamada; el video requiere un proceso de envío y consulta continua (submit-then-poll).
4. **Registro (Log)** — escribe el archivo JSON de registro (sidecar) junto al archivo guardado.

## Las reglas y límites (Guardrails)

Casi todo en esta skill es una restricción, y son estas restricciones las que la hacen útil en el día a día en lugar de limitarla:

- **Cotización antes de video.** El video es el flujo más costoso. La skill indica el modelo, la duración y los dólares esperados, y luego espera un consentimiento explícito. Una aprobación cubre exactamente una ejecución.
- **Borrador económico, acabado de calidad.** Itera en Nano Banana 2 Lite; solo vuelve a ejecutar en Pro una vez que hayas elegido tu borrador favorito. Dejas de pagar precios premium por borradores desechables.
- **Referencias reales, nunca descritas.** Si falta una imagen de referencia necesaria, la skill se detiene y la solicita en lugar de aproximar tu marca a partir de una descripción de texto.
- **Una carpeta plana.** Cada archivo generado se guarda directamente en `~/generations`, sin subcarpetas. Cualquier galería, script o búsqueda simple en la carpeta puede leer toda tu biblioteca de medios sin configuración adicional.
- **Un archivo de registro (sidecar) al lado de cada archivo.** Mismo nombre base, extensión `.json`. Ese es todo el contrato, lo que significa que ningún prompt se pierde:

```json
{
  "model": "gemini-3.1-flash-lite-image",
  "prompt": "el prompt exacto enviado",
  "reference_images": ["generations/refs/logo.png"],
  "params": { "aspect_ratio": "16:9", "image_size": "1K" },
  "cost": "$0.04",
  "created": "2026-07-31T14:20:00Z",
  "approved_by_user": true
}
```

## Qué hay aquí

```
SKILL.md                          el cerebro: tabla de ruteo, reglas, contrato de registro
models/
  nano-banana-2-lite.md           receta de borrador de imagen — síncrono, económico, predeterminado
  nano-banana-pro.md              receta de imagen de calidad — hasta 14 imágenes de referencia
  gemini-omni-flash.md            receta de video — asíncrono (submit-then-poll), audio sincronizado
```

Después de instalar, verifica que la carpeta `models/` se haya colocado junto a `SKILL.md` en tu directorio de skills. La tabla de ruteo apunta a esos archivos de recetas, por lo que si solo se transfirió `SKILL.md`, las generaciones fallarán en el paso de "leer la receta".

## Lo que esto no es

**No es un reemplazo de Flow.** Google Flow es la interfaz creativa para estos mismos modelos: construcción de escenas toma por toma, controles de cámara, edición precisa de fotogramas. Flow es una interfaz web sin API, por lo que cuando un trabajo necesita herramientas al estilo de Flow, la skill lo indica y te redirige allí en lugar de simularlo mediante llamadas a la API.

**No es gratuito.** Las imágenes cuestan centavos, pero el video se factura por segundo y unos pocos clips pueden acumularse rápidamente. Es precisamente por eso que existe el paso de aprobación y por qué la skill nunca ejecutará un trabajo de video de forma especulativa. Monitorea tu uso durante el primer día.

**No es multiproveedor.** Sin Kling, sin Seedance, sin Sora, sin enrutamiento de respaldo entre agregadores. Esta es una decisión deliberada: una única ruta de autenticación y acceso inmediato a las funciones de Gemini, a costa de la variedad de modelos. Si necesitas modelos que no sean de Google bajo una misma clave, considera usar envoltorios tipo Higgsfield en su lugar — diferente herramienta, diferente decisión.

**Los IDs de modelos en vista previa cambiarán.** `gemini-3-pro-image-preview` y `gemini-omni-flash-preview` son nombres de vista previa. Si una llamada devuelve "model not found" (modelo no encontrado), consulta la [documentación de la API de Gemini](https://ai.google.dev/gemini-api/docs) para obtener el ID actual y actualiza el archivo de receta correspondiente. Ese es el único mantenimiento que requiere este sistema.

## Licencia

MIT (consulta el archivo `LICENSE` para más detalles).
