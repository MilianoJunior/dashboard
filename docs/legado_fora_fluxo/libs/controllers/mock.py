gauges = [
    {
        "id": "ug_01",
        "name": "UG-01",
        "status": "operando",  # operando | atencao | critico | parado
        "metrics": {
            "potencia_ativa_kw": 0.0,
            "potencia_instalada_kw": 7500.0,
            "percentual": 0.0
        },
        "timestamp": None
    },
    {
        "id": "ug_02",
        "name": "UG-02",
        "status": "operando",
        "metrics": {
            "potencia_ativa_kw": 0.0,
            "potencia_instalada_kw": 7500.0,
            "percentual": 0.0
        },
        "timestamp": None
    },
    {
        "id": "ug_03",
        "name": "UG-03",
        "status": "atencao",
        "metrics": {
            "potencia_ativa_kw": 0.0,
            "potencia_instalada_kw": 7500.0,
            "percentual": 0.0
        },
        "timestamp": None
    },
    {
        "id": "ug_04",
        "name": "UG-04",
        "status": "critico",
        "metrics": {
            "potencia_ativa_kw": 0.0,
            "potencia_instalada_kw": 7500.0,
            "percentual": 0.0
        },
        "timestamp": None
    },
    {
        "id": "ug_05",
        "name": "UG-05",
        "status": "operando",
        "metrics": {
            "potencia_ativa_kw": 0.0,
            "potencia_instalada_kw": 7500.0,
            "percentual": 0.0
        },
        "timestamp": None
    }
]

geracao = {
    "periodo": {
        "inicio": "2023-10-01",
        "fim": "2023-10-31"
    },
    "unidades": [
        {
            "id": "ug_01",
            "nome": "UG-01",
            "dados": [
                {"timestamp": "2023-10-01", "energia_kwh": 350000},
                {"timestamp": "2023-10-02", "energia_kwh": 370000},
                {"timestamp": "2023-10-03", "energia_kwh": 360000},
            ]
        },
        {
            "id": "ug_02",
            "nome": "UG-02",
            "dados": [
                {"timestamp": "2023-10-01", "energia_kwh": 340000},
                {"timestamp": "2023-10-02", "energia_kwh": 355000},
                {"timestamp": "2023-10-03", "energia_kwh": 365000},
            ]
        }
    ]
}
reservatorios = [
    {
        "id": "res_1",
        "nome": "Reservatório 1",
        "nivel_m": 0.0,
        "nivel_max": 100.0,
        "nivel_min": 20.0,
        "nivel_vertimento": 95.0,
        "timestamp": None
    }
]
# gauges = [
#     {
#         "name": "UG-01",
#         "status": "UPGM",
#         "percent": "0",
#         "power_mw": "0",
#         "potencia_instalada": "7500",
#         "especificacao": "kW",
#     },
#     {
#         "name": "UG-02",
#         "status": "UPGM",
#         "percent": "0",
#         "power_mw": "0",
#         "potencia_instalada": "7500",
#         "especificacao": "kW",
#     },
#     {
#         "name": "UG-03",
#         "status": "UPGM",
#         "percent": "0",
#         "power_mw": "0",
#         "potencia_instalada": "7500",
#         "especificacao": "kW",
#     },
#     {
#         "name": "UG-04",
#         "status": "UPGM",
#         "percent": "0",
#         "power_mw": "0",
#         "potencia_instalada": "7500",
#         "especificacao": "kW",
#     },
#     {
#         "name": "UG-05",
#         "status": "UPGM",
#         "percent": "0",
#         "power_mw": "0",
#         "potencia_instalada": "7500",
#         "especificacao": "kW",
#     },
# ]

# geracao = [

# ]