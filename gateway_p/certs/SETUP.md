# Configuración de Certificados SSL para Banco de Comercio

## 📋 Pasos para configurar los certificados:

### 1. Coloca tus certificados en este directorio

El banco te proporcionó 2 archivos principales:

```
certs/
├── bdc_client_cert.pem      # Certificado público (archivo .pem o .crt)
├── bdc_client_key.pem       # Clave privada (archivo .pem o .key)
└── bdc_ca_cert.pem          # (Opcional) Certificado de la CA del banco
```

**Nombres sugeridos pero configurables** - puedes usar los nombres que quieras y configurarlos en `.env`

### 2. Configura las rutas en tu archivo `.env`

Copia estas líneas en tu archivo `.env` y ajusta las rutas si usas nombres diferentes:

```env
# Certificados SSL del Banco de Comercio
bdc_client_cert_path=./certs/bdc_client_cert.pem
bdc_client_key_path=./certs/bdc_client_key.pem
api-cert-ca=./certs/bdc_ca_cert.pem
```

### 3. Verifica los permisos de los archivos

En Linux/Mac, asegúrate de que solo tu usuario pueda leer los certificados:

```bash
chmod 600 certs/*.pem
chmod 600 certs/*.key
```

En Windows, los permisos se gestionan automáticamente.

### 4. Reinicia los contenedores

```bash
docker compose down
docker compose up -d --build
```

## 🔒 Seguridad

- ✅ Los certificados están excluidos del git (ver `.gitignore`)
- ✅ Los certificados se montan como **read-only** en Docker
- ✅ Nunca compartas estos archivos públicamente
- ✅ No los incluyas en repositorios públicos

## 🧪 Testing

Para verificar que los certificados están configurados correctamente:

```bash
# Endpoint de healthcheck
curl -X 'GET' 'http://localhost:8000/bdc/healthcheck' -H 'accept: application/json'
```

Si está correctamente configurado, debería responder sin errores SSL.

## ❓ Troubleshooting

### Error: "Certificado de cliente no encontrado"

- Verifica que las rutas en `.env` sean correctas
- Asegúrate de que los archivos existan en el directorio `certs/`

### Error: "SSL: CERTIFICATE_VERIFY_FAILED"

- Si estás en **sandbox/testing** y NO tienes certificados, el sistema automáticamente deshabilitará la verificación SSL
- Si estás en **producción**, asegúrate de tener todos los certificados configurados

### Los certificados no se cargan en Docker

- Reinicia los contenedores: `docker compose restart`
- Verifica que el volumen esté montado: `docker compose config`
