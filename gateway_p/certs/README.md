# Certificados del Banco de Comercio

Este directorio contiene los certificados SSL requeridos para la comunicación con el API del Banco de Comercio.

## Archivos requeridos:

- `bdc_client_cert.pem` - Certificado público del cliente
- `bdc_client_key.pem` - Clave privada del cliente
- `bdc_ca_cert.pem` - (Opcional) Certificado de la CA del banco

## ⚠️ IMPORTANTE - Seguridad

Estos archivos **NO** deben ser versionados en Git. Ya están incluidos en `.gitignore`.

## Configuración

Las rutas a estos certificados se configuran en el archivo `.env`:

```env
BDC_CLIENT_CERT_PATH=./certs/bdc_client_cert.pem
BDC_CLIENT_KEY_PATH=./certs/bdc_client_key.pem
api-cert-ca=./certs/bdc_ca_cert.pem
```

## Despliegue en Docker

En docker-compose.yml, estos certificados se montan como volumen para que estén disponibles en el contenedor.
