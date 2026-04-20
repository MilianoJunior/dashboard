import requests

BASE_URL = "http://servidor.ambitec.eng.br:8080/sistema"
LOGIN_URL = f"{BASE_URL}/engine.php?class=LoginForm&method=onLogin"

session = requests.Session()
payload = {
    "login": "pchpira",
    "password": "PIRA",
    "class": "LoginForm",
    "method": "onLogin"
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": f"{BASE_URL}/index.php?class=LoginForm",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
}

print("Fazendo login...")
resp = session.post(LOGIN_URL, data=payload, headers=headers)
print(resp.status_code)
print(session.cookies.get_dict())
