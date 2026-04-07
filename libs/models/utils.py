# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _formatar_decimal_br     -> Formata decimal no padrão brasileiro
# 2. _formatar_datetime_br    -> Formata data/hora para templates
# 3. register_template_filters -> Registra filtros globais do Jinja
# -------------------------------------------------------------------

from datetime import date, datetime


def _formatar_decimal_br(valor, casas=2):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return valor

    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "v").replace(".", ",").replace("v", ".")


def _formatar_datetime_br(valor, formato="%d/%m/%Y %H:%M"):
    if isinstance(valor, datetime):
        return valor.strftime(formato)

    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")

    return valor


def register_template_filters(app):
    @app.template_filter("decimal_br")
    def decimal_br(valor, casas=2):
        return _formatar_decimal_br(valor, casas)

    @app.template_filter("datetime_br")
    def datetime_br(valor, formato="%d/%m/%Y %H:%M"):
        return _formatar_datetime_br(valor, formato)

    return app
