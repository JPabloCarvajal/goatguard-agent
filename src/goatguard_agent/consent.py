"""
Data treatment consent manager for GOATGuard agent.

Colombian Law 1581/2012 (Data Protection) and Decree 1377/2013
require informed consent before collecting personal data.
Network traffic metadata (IPs, ports, protocols, timestamps)
constitutes personal data under SIC interpretation.

The agent MUST NOT capture any traffic until the user
accepts the data treatment policy. Acceptance is recorded
locally in a consent file with timestamp.

Legal references:

# ┌─────────────────┬─────────┬──────────────────────────────┬────────────────────────────────────────────┐
# │ Ley             │ Art.    │ Qué regula                   │ Impacto en GOATGuard                       │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 1273/2009   │ 269A    │ Acceso abusivo a sistema     │ Agente requiere autorizacion del dueño     │
# │                 │         │ informatico                  │ de la red                                  │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 1273/2009   │ 269C    │ Interceptacion de datos      │ Captura de paquetes requiere facultacion   │
# │                 │         │ informaticos                 │                                            │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 1581/2012   │ Art. 4  │ Principio de libertad        │ Usuarios deben saber que se monitorea      │
# │                 │         │ (consentimiento)             │                                            │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 1581/2012   │ Art. 4  │ Principio de finalidad       │ Solo capturar para monitoreo, no espiar    │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 1581/2012   │ Art. 6  │ Excepcion cientifica         │ Aplica al proyecto academico con           │
# │                 │         │                              │ anonimizacion                              │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Decreto 1377/13 │ Art. 3  │ Aviso de privacidad          │ Informar al usuario antes de recopilar     │
# ├─────────────────┼─────────┼──────────────────────────────┼────────────────────────────────────────────┤
# │ Ley 2466/2025   │ Monit.  │ Consentimiento explicito     │ En entorno empresarial, el empleado        │
# │                 │         │ del trabajador               │ debe aceptar                               │
# └─────────────────┴─────────┴──────────────────────────────┴────────────────────────────────────────────┘
"""

import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

CONSENT_FILE = Path.home() / ".goatguard_consent"

CONSENT_TEXT = """
================================================================================
        GOATGuard — Aviso de Tratamiento de Datos Personales
================================================================================

RESPONSABLE DEL TRATAMIENTO
GOATGuard Network Monitoring System, operado por el administrador de la red
local donde se despliega este agente.

ESTE SISTEMA ES UNA HERRAMIENTA INVESTIGATIVA Y DE MONITOREO

DATOS QUE SE RECOPILAN
Este agente recopila los siguientes datos del equipo donde se instala:
  - Direcciones IP de origen y destino de las conexiones de red
  - Puertos y protocolos utilizados (TCP, UDP, DNS, HTTP, HTTPS)
  - Timestamps de inicio y fin de cada conexion
  - Volumen de datos transmitidos (bytes enviados y recibidos)
  - Estados de conexion TCP (establecida, fallida, rechazada)
  - Metricas del sistema: uso de CPU, RAM, disco, velocidad del enlace
  - Direccion MAC e identificador del equipo (hostname)

DATOS QUE NO SE RECOPILAN
  - Contenido de comunicaciones cifradas (HTTPS, TLS, SSH)
  - Contenido de correos electronicos, mensajes o archivos
  - Contrasenas, tokens de autenticacion o credenciales
  - Contenido de navegacion web (solo dominios destino, no URLs completas)
  - Datos biometricos, financieros o de salud

FINALIDAD DEL TRATAMIENTO
Los datos se recopilan exclusivamente para:
  - Monitoreo del estado de la infraestructura de red
  - Deteccion de anomalias de trafico y comportamientos inusuales
  - Identificacion de dispositivos conectados a la red
  - Generacion de metricas de rendimiento y alertas de seguridad
  - Elaboracion de estadisticas de uso de la red

Los datos NO se utilizan para vigilancia de contenido de comunicaciones,
evaluacion de productividad laboral, ni perfilamiento de usuarios.

ALMACENAMIENTO Y RETENCION
  - Los datos se almacenan en un servidor central dentro de la red local
  - Las metricas actuales se sobreescriben cada 30 segundos
  - Los historicos se retienen por un periodo maximo de 30 dias
  - Los datos no se transfieren a servidores externos ni a la nube

DERECHOS DEL TITULAR (Ley 1581 de 2012, Art. 8)
Usted tiene derecho a:
  - Conocer que datos se han recopilado de su equipo
  - Solicitar la actualizacion o rectificacion de sus datos
  - Solicitar la eliminacion de sus datos del sistema
  - Solicitar la desinstalacion del agente de su equipo
  - Revocar esta autorizacion en cualquier momento

Para ejercer estos derechos, contacte al administrador de la red.

BASE LEGAL
  - Ley 1581 de 2012 (Proteccion de Datos Personales)
  - Decreto 1377 de 2013 (Reglamentario de la Ley 1581)
  - Ley 1273 de 2009 (Delitos Informaticos, Art. 269C)

================================================================================
"""


def check_consent() -> bool:
    """Check if the user has previously accepted the data policy.

    Returns:
        True if consent was previously given, False otherwise.
    """
    if CONSENT_FILE.exists():
        logger.info("Previous consent found, proceeding with capture")
        return True
    return False


def request_consent() -> bool:
    """Display the data treatment policy and request acceptance.

    Shows the full policy text and asks for explicit acceptance.
    Records the acceptance with timestamp if granted.

    Returns:
        True if user accepted, False if declined.
    """
    print(CONSENT_TEXT)
    print("================================================================================")
    print("  Para continuar, debe aceptar esta politica de tratamiento de datos.")
    print("  El agente NO capturara ningun dato hasta que usted acepte.")
    print("================================================================================")
    print()

    while True:
        response = input("  Acepta la politica de tratamiento de datos? (si/no): ").strip().lower()

        if response in ("si", "s", "yes", "y"):
            _record_consent()
            print()
            print("  Consentimiento registrado. El agente iniciara la captura.")
            print()
            return True

        elif response in ("no", "n"):
            print()
            print("  Consentimiento denegado. El agente NO se ejecutara.")
            print("  Puede ejecutar el agente nuevamente si cambia de opinion.")
            print()
            return False

        else:
            print("  Por favor responda 'si' o 'no'.")


def _record_consent() -> None:
    """Record the consent acceptance with timestamp.

    Creates a file in the user's home directory with the
    date and time of acceptance. This file is checked on
    subsequent runs to avoid asking again.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    consent_data = (
        f"GOATGuard Data Treatment Consent\n"
        f"Accepted: {timestamp}\n"
        f"User: {os.getlogin()}\n"
        f"Host: {os.uname().nodename if hasattr(os, 'uname') else 'unknown'}\n"
    )

    try:
        CONSENT_FILE.write_text(consent_data)
        logger.info(f"Consent recorded at {CONSENT_FILE}")
    except Exception as e:
        logger.error(f"Failed to record consent: {e}")
        # Still allow execution if file write fails
        # The consent was given verbally


def revoke_consent() -> None:
    """Revoke previously given consent.

    Deletes the consent file. The agent will ask for
    consent again on next execution.
    """
    if CONSENT_FILE.exists():
        CONSENT_FILE.unlink()
        print("Consentimiento revocado. El agente no capturara datos.")
        print("Ejecute el agente nuevamente para aceptar la nueva politica.")
    else:
        print("No hay consentimiento registrado.")