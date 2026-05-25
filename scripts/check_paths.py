import os
import sys

print(f'Python path: {sys.path[0]}')
print(f'Diretorio atual: {os.getcwd()}')
print(f'Arquivo existe em .: {os.path.exists("./nia_flv.db")}')
print(f'Arquivo existe em path absoluto: {os.path.exists(os.path.join(os.getcwd(), "nia_flv.db"))}')

# Simula o que o crisis_watch faz
from flv.collectors import crisis_watch
print(f'DB_PATH no crisis_watch: {crisis_watch.DB_PATH}')
print(f'Arquivo existe no DB_PATH: {os.path.exists(crisis_watch.DB_PATH)}')
