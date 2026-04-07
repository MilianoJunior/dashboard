# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. Exporta o controller principal do dashboard
# -------------------------------------------------------------------

from .dashboard_controller import get_dashboard_data

__all__ = ["get_dashboard_data"]
