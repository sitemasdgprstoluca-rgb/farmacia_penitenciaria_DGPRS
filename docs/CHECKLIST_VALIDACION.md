# Checklist de Validación Funcional — Videos y Demo

Propósito: Comprobar que cada flujo mostrado en los videos funciona correctamente antes de publicar.

Instrucciones generales
- Ejecutar cada paso en entorno demo limpio (usar `db.sqlite3.backup` si es necesario).
- Abrir frontend en incógnito.
- Mantener backend en consola para revisar logs/emails.

1) Validación del flujo de restablecimiento de contraseña
- [ ] En `recuperar-password` introducir email de prueba válido.
- [ ] Verificar que la API responde 200 y que el correo generado aparece en la consola si usas `console.EmailBackend`.
- [ ] Copiar el `uid` y `token` desde el correo (o desde consola) y abrir la URL `/restablecer-password?uid=<uid>&token=<token>`.
- [ ] Verificar que la página muestra banner con el email identificado (badge azul con `userEmail`).
- [ ] Validar que al escribir la nueva contraseña se actualiza el indicador de fortaleza en tiempo real.
- [ ] Probar distintas contraseñas: débiles, medias, fuertes y comprobar labels y colores.
- [ ] Verificar que los checkmarks aparecen al cumplir requisitos (8+ chars, mayúsculas, número, especial).
- [ ] Confirmar con contraseña coincidente: enviar formulario y comprobar respuesta 200.
- [ ] Verificar pantalla de éxito completa (animaciones, banners de seguridad, recomendaciones).
- [ ] Confirmar redirección automática tras countdown y que `hasNavigated` evita navegación múltiple.
- [ ] Verificar que el enlace ya no es válido si intentas usarlo por segunda vez.

2) UI / Estilo / Colores institucionales
- [ ] Verificar uso de `var(--color-primary)` y `var(--color-primary-hover)` en header, botones y bordes.
- [ ] Comprobar que no aparece el cuadro blanco superior (logo) que fue eliminado.
- [ ] Comprobar responsividad en 1366×768 y 375×812.
- [ ] Verificar contraste y legibilidad (WCAG básico) para títulos y botones.

3) Accesibilidad básica
- [ ] Tab navigation: todos los inputs y botones accesibles mediante `Tab`.
- [ ] Elementos con `aria` o textos alternativos cuando aplica (logo, iconos explicativos).

4) Rendimiento y errores
- [ ] Abrir DevTools → Console: no errores JavaScript durante el flujo.
- [ ] Backend logs: no excepciones durante la confirmación de contraseña.
- [ ] Build local: `npm run build` finaliza sin errores.

5) Integración email (si se prueba envío real)
- [ ] Si usas Resend o SMTP, verificar que correo llega a la bandeja y que el link funciona.
- [ ] Validar plantilla HTML: gradients, texto y enlaces correctos.

6) Seguridad / auditoría
- [ ] Verificar que la API invalida token después de uso.
- [ ] Confirmar que password no se muestra en logs.
- [ ] Revisar que la entrada de contraseña tiene `minLength=8` y validaciones en frontend y backend.

7) Checklist para grabación del video (pre-check antes de grabar)
- [ ] Limpiar cache y abrir ventana de incógnito
- [ ] Cuentas de demo creadas y contraseñas confirmadas
- [ ] Consola del backend visible (para screenshots de email si aplica)
- [ ] Resolución y settings del recorder (1080p, 30fps)
- [ ] Notificaciones/desktops silenciadas

8) Revisión post-grabación
- [ ] Reproducir el video y seguir cada paso de la checklist para confirmar que lo que se muestra coincide con el flujo real.
- [ ] Si hay discrepancias, actualizar demo o regrabar la sección específica.

---
Archivo de referencia: `docs/CHECKLIST_VALIDACION.md` creado automáticamente.
