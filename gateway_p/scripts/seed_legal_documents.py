"""
Script para insertar documentos legales de ejemplo (seed data)

Ejecutar: python -m scripts.seed_legal_documents
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import get_db_session
from app.db.models import LegalDocumentRecord


# Contenido de ejemplo
TERMS_CONTENT = """
<h1>Términos y Condiciones de Uso - Pagoflex</h1>

<h2>1. Aceptación de los Términos</h2>
<p>Al registrarse y utilizar los servicios de Pagoflex, usted acepta estar sujeto a estos Términos y Condiciones.</p>

<h2>2. Descripción del Servicio</h2>
<p>Pagoflex es una plataforma de pagos digitales que permite a los usuarios realizar transferencias, pagos y gestionar su billetera digital de manera segura.</p>

<h2>3. Registro de Usuario</h2>
<p>Para utilizar nuestros servicios, debe:</p>
<ul>
  <li>Proporcionar información veraz y actualizada</li>
  <li>Mantener la confidencialidad de su contraseña</li>
  <li>Ser mayor de edad según la jurisdicción aplicable</li>
  <li>Cumplir con las regulaciones KYC (Know Your Customer)</li>
</ul>

<h2>4. Uso de la Plataforma</h2>
<p>El usuario se compromete a:</p>
<ul>
  <li>No utilizar la plataforma para actividades ilegales</li>
  <li>No intentar vulnerar la seguridad del sistema</li>
  <li>Reportar cualquier actividad sospechosa</li>
  <li>Mantener actualizada su información personal</li>
</ul>

<h2>5. Tarifas y Comisiones</h2>
<p>Pagoflex se reserva el derecho de cobrar comisiones por ciertos servicios. Las tarifas aplicables serán comunicadas al usuario antes de realizar cualquier transacción.</p>

<h2>6. Limitación de Responsabilidad</h2>
<p>Pagoflex no será responsable por:</p>
<ul>
  <li>Pérdidas derivadas del uso indebido de credenciales</li>
  <li>Fallos en servicios de terceros</li>
  <li>Interrupciones temporales del servicio por mantenimiento</li>
</ul>

<h2>7. Modificaciones</h2>
<p>Pagoflex se reserva el derecho de modificar estos términos en cualquier momento. Los usuarios serán notificados de cambios significativos.</p>

<h2>8. Terminación</h2>
<p>Tanto el usuario como Pagoflex pueden terminar la relación contractual en cualquier momento, sujeto a las obligaciones pendientes.</p>

<h2>9. Jurisdicción</h2>
<p>Estos términos se rigen por las leyes de Argentina. Cualquier disputa será resuelta en los tribunales competentes.</p>

<p><strong>Última actualización:</strong> Febrero 2026</p>
"""

PRIVACY_CONTENT = """
<h1>Política de Privacidad y Tratamiento de Datos - Pagoflex</h1>

<h2>1. Introducción</h2>
<p>En Pagoflex valoramos y respetamos su privacidad. Esta política describe cómo recopilamos, usamos y protegemos su información personal.</p>

<h2>2. Información que Recopilamos</h2>
<p>Recopilamos los siguientes tipos de información:</p>

<h3>2.1 Información Personal</h3>
<ul>
  <li>Nombre completo</li>
  <li>Documento de identidad (DNI)</li>
  <li>CUIT/CUIL</li>
  <li>Dirección de correo electrónico</li>
  <li>Número de teléfono</li>
  <li>Ubicación</li>
  <li>Ocupación y estado civil</li>
</ul>

<h3>2.2 Información de Transacciones</h3>
<ul>
  <li>Historial de pagos y transferencias</li>
  <li>Saldos de cuenta</li>
  <li>Información bancaria</li>
</ul>

<h3>2.3 Información Técnica</h3>
<ul>
  <li>Dirección IP</li>
  <li>Tipo de dispositivo y navegador</li>
  <li>Cookies y tecnologías similares</li>
  <li>Registros de acceso y actividad</li>
</ul>

<h2>3. Uso de la Información</h2>
<p>Utilizamos su información para:</p>
<ul>
  <li>Proporcionar y mejorar nuestros servicios</li>
  <li>Verificar su identidad (KYC)</li>
  <li>Procesar transacciones</li>
  <li>Prevenir fraude y garantizar seguridad</li>
  <li>Cumplir con obligaciones legales y regulatorias</li>
  <li>Comunicarnos con usted sobre el servicio</li>
  <li>Analizar y mejorar la experiencia de usuario</li>
</ul>

<h2>4. Compartir Información</h2>
<p>Podemos compartir su información con:</p>
<ul>
  <li><strong>Instituciones financieras:</strong> Para procesar pagos y transferencias</li>
  <li><strong>Proveedores de servicios:</strong> Que nos ayudan a operar la plataforma</li>
  <li><strong>Autoridades:</strong> Cuando sea requerido por ley</li>
  <li><strong>Servicios KYC:</strong> Para verificación de identidad</li>
</ul>

<h2>5. Seguridad de los Datos</h2>
<p>Implementamos medidas de seguridad técnicas y organizativas para proteger su información:</p>
<ul>
  <li>Encriptación de datos en tránsito y en reposo</li>
  <li>Autenticación de dos factores</li>
  <li>Monitoreo continuo de seguridad</li>
  <li>Acceso restringido a información personal</li>
  <li>Auditorías de seguridad regulares</li>
</ul>

<h2>6. Retención de Datos</h2>
<p>Conservamos su información personal mientras su cuenta esté activa y durante el período requerido por la ley para cumplir con obligaciones regulatorias (típicamente 10 años para registros financieros).</p>

<h2>7. Sus Derechos</h2>
<p>Usted tiene derecho a:</p>
<ul>
  <li><strong>Acceso:</strong> Solicitar copia de su información personal</li>
  <li><strong>Rectificación:</strong> Corregir información inexacta</li>
  <li><strong>Eliminación:</strong> Solicitar eliminación de sus datos (sujeto a obligaciones legales)</li>
  <li><strong>Portabilidad:</strong> Recibir sus datos en formato estructurado</li>
  <li><strong>Oposición:</strong> Oponerse a ciertos tipos de procesamiento</li>
  <li><strong>Revocación:</strong> Revocar consentimientos otorgados</li>
</ul>

<h2>8. Cookies</h2>
<p>Utilizamos cookies para mejorar la funcionalidad y experiencia de usuario. Puede configurar su navegador para rechazar cookies, aunque esto puede limitar algunas funcionalidades.</p>

<h2>9. Transferencias Internacionales</h2>
<p>Sus datos pueden ser transferidos y procesados en servidores ubicados fuera de Argentina, siempre con garantías adecuadas de protección.</p>

<h2>10. Menores de Edad</h2>
<p>Nuestros servicios no están dirigidos a menores de 18 años. No recopilamos intencionalmente información de menores.</p>

<h2>11. Cambios a esta Política</h2>
<p>Podemos actualizar esta política periódicamente. Los cambios significativos serán notificados mediante correo electrónico o aviso en la plataforma.</p>

<h2>12. Contacto</h2>
<p>Para consultas sobre privacidad, contáctenos en: privacy@pagoflex.com</p>

<p><strong>Última actualización:</strong> Febrero 2026</p>
<p><strong>Versión:</strong> 1.0</p>
"""


async def seed_legal_documents():
    """Inserta documentos legales de ejemplo si no existen"""
    
    async for session in get_db_session():
        try:
            # Verificar si ya existen documentos
            stmt = select(LegalDocumentRecord)
            result = await session.execute(stmt)
            existing = result.scalars().all()
            
            if existing:
                print(f"⚠️  Ya existen {len(existing)} documentos legales en la base de datos.")
                print("    Para regenerar, elimínalos primero o usa otro script.")
                return
            
            # Fecha efectiva (hoy)
            effective_date = datetime.now(timezone.utc)
            
            # Crear Términos y Condiciones
            terms = LegalDocumentRecord(
                document_type="terms_and_conditions",
                version="1.0",
                title="Términos y Condiciones de Uso",
                content=TERMS_CONTENT.strip(),
                is_active=True,
                effective_date=effective_date,
            )
            session.add(terms)
            
            # Crear Política de Privacidad
            privacy = LegalDocumentRecord(
                document_type="privacy_policy",
                version="1.0",
                title="Política de Privacidad y Tratamiento de Datos",
                content=PRIVACY_CONTENT.strip(),
                is_active=True,
                effective_date=effective_date,
            )
            session.add(privacy)
            
            await session.commit()
            
            print("✅ Documentos legales insertados exitosamente:")
            print(f"   - Términos y Condiciones v1.0 (ID: {terms.id})")
            print(f"   - Política de Privacidad v1.0 (ID: {privacy.id})")
            print()
            print("📋 Siguiente paso:")
            print("   - Accede a GET /legal/terms para ver los términos")
            print("   - Accede a GET /legal/privacy para ver la política")
            print("   - Los usuarios deberán aceptarlos con POST /legal/accept")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error al insertar documentos legales: {e}")
            raise


if __name__ == "__main__":
    print("🔐 Insertando documentos legales de ejemplo...\n")
    asyncio.run(seed_legal_documents())
