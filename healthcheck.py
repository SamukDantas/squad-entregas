from datetime import datetime, timezone

VERSION = "1.0.0"


def get_health_status() -> bool:
    """Verifica o status atual do sistema.

    Returns:
        bool: True se o sistema estiver operacional, False caso contrario.
    """
    return True


def build_healthcheck_response():
    """Constroi o dicionario de resposta do healthcheck.

    Returns:
        dict: Dicionario com os campos status, version e timestamp.
    """
    status = "ok" if get_health_status() else "error"
    return {
        "status": status,
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
