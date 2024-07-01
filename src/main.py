'''
Codigo desarrollador por @gatoartstudio y usando la base de datos de https://github.com/WebBreacher/WhatsMyName,
la cual nos proporciona una lista de sitios webs potenciales para buscar un usuario, y la cual se actualiza constante.
'''

import json
import time
import requests
import colorama
import argparse
import pyfiglet
from tqdm import tqdm
from tabulate import tabulate
import concurrent.futures
from requests.exceptions import ConnectionError, Timeout, RequestException
from urllib3.exceptions import InsecureRequestWarning

# Suprimir las advertencias de solicitudes HTTPS no verificadas
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

parser = argparse.ArgumentParser(prog='main.py', description='Comprueba si una cuenta está en un sitio web', epilog='By @gatoartstudio')
parser.add_argument('-a', '--account', required=True, help='La cuenta a verificar, Ejemplo: main.py -a testuser', dest='ACCOUNT')
parser.add_argument('-t', help='Cantidad de hilos a usar', default=20, type=int, dest='THREADS')
args = parser.parse_args()
account_to_check = args.ACCOUNT
threads = args.THREADS

colorama.init(autoreset=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
}

print(f'{colorama.Fore.CYAN}\n\n{pyfiglet.figlet_format('OsintCat', font='speed', justify='center')}')
print(f'{colorama.Fore.CYAN}[+] Conectando con la base de datos de webs disponibles y actualizada')
try:
    response = requests.get('https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json')
    if response.status_code == 200:
        data = response.json()
        print(f'{colorama.Fore.CYAN}[+] Cantidad de sitios: {len(data["sites"])}, Usuario: {account_to_check}\n')
    else:
        print(f'{colorama.Fore.RED}Error al conectar con la base de datos: Status code {response.status_code}')
        exit(1)
except Exception as e:
    print(f'{colorama.Fore.RED}Error al conectar con la base de datos:', e)
    exit(1)

def check_account(site, account, retries=3):
    url = site["uri_check"].format(account=account.replace(" ", "%20"))
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers if not site.get("headers") else site["headers"], timeout=10, verify=False)
            if response.status_code == site["e_code"] and site["e_string"] in response.text:
                return (site['name'], url, True)
            elif response.status_code == site["m_code"] and site["m_string"] in response.text:
                return (site['name'], url, False)
            else:
                return (site['name'], url, None)
        except (ConnectionError, Timeout) as e:
            time.sleep(2 ** attempt)
        except RequestException as e:
            return (site['name'], url, None)
    return (site['name'], url, None)

def osint_check(account):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(check_account, site, account): site for site in data["sites"]}
        total_sites = len(data["sites"])
        progress_bar = tqdm(total=total_sites, desc=f"{colorama.Fore.CYAN}[::] Verifying account {account} on OSINT sites", dynamic_ncols=False)
        for future in concurrent.futures.as_completed(futures):
            site = futures[future]
            try:
                result = future.result()
                results[site["name"]] = result
                progress_bar.update(1)
            except Exception as e:
                results[site["name"]] = (site['name'], None, None)
                progress_bar.update(1)
        progress_bar.close()
    return results

results = osint_check(account_to_check)
validos = [site for site, result in results.items() if result[2] is True]
print(f'{colorama.Fore.CYAN}\n[+] Se encontraron {len(validos)} sitios donde [{account_to_check}] existe\n')
data_tables = [['Sitio', 'Cuenta', 'URL']]
for site, result in results.items():
    url = result[1]
    if result[2] is True:
        data_tables.append([site, account_to_check, url])
print(f'{colorama.Fore.CYAN}{tabulate(data_tables, headers="firstrow", tablefmt="fancy_grid")}')
