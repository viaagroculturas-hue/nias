"""
CEASA Scheduler — Agendamento automático de coleta diária
Executa de segunda a sexta-feira às 11:00
"""
import schedule
import time
from datetime import datetime
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from flv.collectors.ceasa_consolidador import run_coleta_completa

def job_coleta_ceasa():
    """Job de coleta das CEASAs"""
    print(f"\n{'='*60}")
    print(f"AGENDAMENTO CEASA — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        resultado = run_coleta_completa()
        if resultado:
            print(f"\n✓ Coleta agendada concluída: {resultado}")
        else:
            print("\n✗ Coleta falhou")
    except Exception as e:
        print(f"\n✗ Erro na coleta: {e}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    """Inicia o agendador"""
    print(f"""
{'='*60}
CEASA SCHEDULER
{'='*60}
Agendamento: Segunda a Sexta-feira às 11:00
Próxima execução: {schedule.next_run()}

Pressione Ctrl+C para interromper.
{'='*60}
""")
    
    # Agendar para seg-sex às 11:00
    schedule.every().monday.at("11:00").do(job_coleta_ceasa)
    schedule.every().tuesday.at("11:00").do(job_coleta_ceasa)
    schedule.every().wednesday.at("11:00").do(job_coleta_ceasa)
    schedule.every().thursday.at("11:00").do(job_coleta_ceasa)
    schedule.every().friday.at("11:00").do(job_coleta_ceasa)
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto

def run_once():
    """Executa coleta uma vez (para teste)"""
    job_coleta_ceasa()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CEASA Scheduler')
    parser.add_argument('--once', action='store_true', help='Executa uma vez e sai')
    parser.add_argument('--now', action='store_true', help='Executa imediatamente')
    
    args = parser.parse_args()
    
    if args.once or args.now:
        run_once()
    else:
        run_scheduler()
