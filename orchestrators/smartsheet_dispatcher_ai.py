from datetime import datetime, timedelta
import datetime as dt
import signal

from core.settings import settings
from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.frontend_mapping.api_mapping_site import send_execution_mapping
from services.apontamento_impar.apontamento_impar import ApontamentoImpar

from utils.driver_factory import DriverFactory


class SmartsheetDispatcher:
    @staticmethod
    def main(worker_id: int, total_workers: int = 1):
        stop_requested = False

        def _handle_shutdown(signum, _frame):
            nonlocal stop_requested
            stop_requested = True
            print(f"[dispatcher_ai] Sinal {signum} recebido. Encerrando com flush pendente...")

        signal.signal(signal.SIGTERM, _handle_shutdown)
        signal.signal(signal.SIGINT, _handle_shutdown)
        sheet, _, token, sheet_id, _ = SmartsheetClient.setup_smartsheet(settings.SHEET_ID_APONTAMENTO_IMPAR)
        nome_coluna_para_indice = {coluna.title: index for index, coluna in enumerate(sheet.columns)}

        if worker_id < 1 or worker_id > total_workers:
            raise ValueError(f"worker_id deve estar entre 1 e {total_workers}")

        total = len(sheet.rows)
        base, resto = divmod(total, total_workers)
        indice_worker = worker_id - 1
        start = indice_worker * base + min(indice_worker, resto)
        end = start + base + (1 if indice_worker < resto else 0)

        bloco_linhas = sheet.rows[start:end]

        driver = DriverFactory.create_edge_driver()
        batch_size = 50
        execution_start_time = datetime.now()
        all_updates = []
        try:
            for linha in bloco_linhas:
                updates = []
                if stop_requested:
                    print("[dispatcher_ai] Interrupcao solicitada, finalizando loop para aplicar update_bulk.")
                    break
                dados_celulas = {
                    coluna.title: linha.cells[nome_coluna_para_indice[coluna.title]].value
                    for coluna in sheet.columns
                    if coluna.title in nome_coluna_para_indice
                }

                data_registro_str = dados_celulas.get('Data_do_Registro', None)
                data_registro_EUA = datetime.strptime(data_registro_str, "%Y-%m-%d")
                data_registro     = data_registro_EUA.strftime("%d/%m/%Y")
                link1_ponto       = dados_celulas.get('Link1', None)
                status            = dados_celulas.get('Status', None)
                motivo_recusa     = dados_celulas.get('Motivo Recusa', None)
                colaborador       = dados_celulas.get('Colaborador', None)
                entrada           = dados_celulas.get('Marcação/Entrada', None)
                saida             = dados_celulas.get('Horário de Saída', None)
                intervalo         = dados_celulas.get('Tempo de Intervalo', None)
                cpf               = colaborador.split("-")[0].strip() if colaborador and "-" in colaborador else None
                cpf               = str(cpf).zfill(11) if cpf is not None else None

                if intervalo is not None:
                    horas, minutos = map(int, intervalo.split(":"))
                    intervalo = timedelta(hours=horas, minutes=minutos)

                hora_informada = dados_celulas.get('Marcação/Entrada', None)
                if hora_informada and hora_informada != "Preencher HC":
                    hora_informada = dt.datetime.strptime(hora_informada, "%H:%M").time()

                classificacao    = dados_celulas.get('Classificação da Falta', None)
                motivo_alteracao = dados_celulas.get('Motivo Alteração', None)
                motivo_alteracao_normalizado = str(motivo_alteracao).strip().lower()
                row_id           = linha.id
                linha_numero     = linha.row_number

                if status is None:
                    print(f"linha {linha_numero} - Colaborador: {colaborador} - Data: {data_registro} Classificação: {classificacao}")

                    driver.get(link1_ponto)
                    match str(motivo_alteracao).strip().lower():
                        case "02.1 - apontamento ímpar":
                            service = ApontamentoImpar(
                                driver=driver,
                                row_id=row_id,
                                sheet_id=sheet_id,
                                token=token,
                                data_registro=data_registro,
                                hora_informada=hora_informada
                            )
                            updates = service.adjust()

                    if updates:
                        all_updates.append({
                            "row_id": row_id,
                            "updates": updates
                        })
                        if len(all_updates) >= batch_size:
                            batch_count = len(all_updates)
                            try:
                                SmartsheetClient.update_bulk(all_updates, settings.SHEET_ID_APONTAMENTO_IMPAR)
                            finally:
                                send_execution_mapping("apontamento_impar", "Apontamento impar", batch_count, execution_start_time, running=True)
                                all_updates.clear()

        except Exception as e:
            print(f'erro: {e}')
        finally:
            driver.quit()
            if all_updates:
                final_count = len(all_updates)
                try:
                    SmartsheetClient.update_bulk(all_updates, settings.SHEET_ID_APONTAMENTO_IMPAR)
                finally:
                    send_execution_mapping("apontamento_impar", "Apontamento impar", final_count, execution_start_time, running=False)
            else:
                print("[dispatcher_ai] Nenhum update pendente; enviando status para API com 0 linhas.")
                send_execution_mapping("apontamento_impar", "Apontamento impar", 0, execution_start_time, running=False)


if __name__ == "__main__":
    import sys
    SmartsheetDispatcher.main(int(sys.argv[1]))

