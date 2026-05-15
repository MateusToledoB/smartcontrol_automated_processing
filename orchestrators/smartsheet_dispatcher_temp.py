from datetime import datetime, timedelta
import datetime as dt
import signal


from core.settings import settings
from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.frontend_mapping.api_mapping_site import send_execution_mapping
from services.temporarios.problema_no_equipamento.horario_contratual_previsto_temp import HorarioContratualPrevistoTemp
from services.temporarios.problema_no_equipamento.informar_horario_realizado_temp import InformarHorarioRealizadoTemp
from services.temporarios.problema_no_equipamento.falta_abono_temp import FaltaAbonoTemp
from services.temporarios.apontamento_impar.apontamento_impar_temp import ApontamentoImparTemp
from services.temporarios.problema_no_equipamento.falta_com_desconto_bh_temp import FaltaDescontoBHTemp

from utils.driver_factory import DriverFactory
from utils.selenium_utils import SeleniumUtils

class SmartsheetDispatcher:
    @staticmethod
    def main(worker_id: int, total_workers: int = 1):
        stop_requested = False

        def _handle_shutdown(signum, _frame):
            nonlocal stop_requested
            stop_requested = True
            print(f"[dispatcher_temp] Sinal {signum} recebido. Encerrando com flush pendente...")

        signal.signal(signal.SIGTERM, _handle_shutdown)
        signal.signal(signal.SIGINT, _handle_shutdown)
        sheet, _, token, sheet_id, _ = SmartsheetClient.setup_smartsheet(settings.SHEET_ID_TEMPORARIOS)
        nome_coluna_para_indice = {coluna.title: index for index, coluna in enumerate(sheet.columns)}
        if worker_id < 1 or worker_id > total_workers:
            raise ValueError(f"worker_id deve estar entre 1 e {total_workers}")

        total = len(sheet.rows)
        base, resto = divmod(total, total_workers)
        indice_worker = worker_id - 1
        start = indice_worker * base + min(indice_worker, resto)
        end = start + base + (1 if indice_worker < resto else 0)

        bloco_linhas = sheet.rows[start:end]

        batch_size = 50
        execution_start_time = datetime.now()
        all_updates = []
        driver = DriverFactory.create_edge_driver()

        SeleniumUtils.login_motus(driver, settings.USER_MOTUS, settings.PASSWORD_MOTUS)
        try:
            for linha in bloco_linhas:
                updates = []
                if stop_requested:
                    print("[dispatcher_temp] Interrupcao solicitada, finalizando loop para aplicar update_bulk.")
                    break
          
                dados_celulas = {coluna.title: linha.cells[nome_coluna_para_indice[coluna.title]].value
                                    for coluna in sheet.columns
                                    if coluna.title in nome_coluna_para_indice}

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
                cpf = colaborador.split("-")[0].strip() if colaborador and "-" in colaborador else None
                cpf = str(cpf).zfill(11) if cpf is not None else None
                if intervalo != None:
                    horas, minutos = map(int, intervalo.split(":"))
                    intervalo = timedelta(hours=horas, minutes=minutos)
                #hora informada no smart
                hora_informada = dados_celulas.get('Marcação/Entrada', None)
                if hora_informada and hora_informada != "Preencher HC":
                    hora_informada = dt.datetime.strptime(hora_informada, "%H:%M").time()
                classificacao     = dados_celulas.get('Classificação da Falta', None)
                motivo_alteracao  = dados_celulas.get('Motivo Alteração', None)
                motivo_alteracao_normalizado = str(motivo_alteracao).strip().lower()
                row_id            = linha.id
                linha_numero      = linha.row_number

                if str(motivo_alteracao).strip().lower() == '02.1 - apontamento ímpar':
                    classificacao = '02.1 - apontamento ímpar'
        
                if status == None:
                    
                    print(f"linha {linha_numero} - Colaborador: {colaborador} - Data: {data_registro} Classificação: {classificacao}")
                    
                    SeleniumUtils.search_cpf(driver, cpf, data_registro)
                    
                    match str(classificacao).strip().lower():
                        case "horário contratual previsto (problema no equipamento)":
                            service = HorarioContratualPrevistoTemp(
                                driver=driver,
                                row_id=row_id,
                                sheet_id=sheet_id,
                                token=token,
                                data_registro=data_registro,
                            )
                            updates = service.adjust()
                            driver.refresh()

                        case "problema no equipamento - informar horário realizado":
                            service = InformarHorarioRealizadoTemp(
                                driver=driver,
                                row_id=row_id,
                                sheet_id=sheet_id,
                                token=token,
                                data_registro=data_registro,
                                entrada=entrada,
                                saida=saida,
                                intervalo=intervalo
                            )
                            updates = service.adjust()
                            driver.refresh()

                        case "abandono" | "atraso" | "falta" | "suspensão" | "integração cliente" | "reciclagem" | "liberado pelo cliente":
                            
                            if motivo_alteracao_normalizado == '04.1 - faltas sem justificativa':     
                                service = FaltaAbonoTemp(
                                    driver=driver,
                                    row_id=row_id,
                                    sheet_id=sheet_id,
                                    token=token,
                                    data_registro = data_registro,
                                    classificacao_falta_lancado = classificacao
                                )
                                updates = service.adjust()
                                driver.refresh()
                            
                            elif motivo_alteracao_normalizado == '09.1 - b.h. negativo':
                                service = FaltaDescontoBHTemp(
                                    driver=driver,
                                    row_id=row_id,
                                    sheet_id=sheet_id,
                                    token=token,
                                    data_registro=data_registro,
                                    classificacao_falta_lancado=classificacao
                                )
                                updates = service.adjust()
                                driver.refresh()

                        case "02.1 - apontamento ímpar":
                            service = ApontamentoImparTemp(
                                driver=driver,
                                row_id=row_id,
                                sheet_id=sheet_id,
                                token=token,
                                data_registro=data_registro,
                                hora_informada=hora_informada
                            )
                            updates = service.adjust()
                            driver.refresh()

                    if updates:
                        all_updates.append({
                            "row_id": row_id,
                            "updates": updates
                        })
                        if len(all_updates) >= batch_size:
                            batch_count = len(all_updates)
                            try:
                                SmartsheetClient.update_bulk(all_updates, settings.SHEET_ID_TEMPORARIOS)
                            finally:
                                send_execution_mapping("temporarios", "Temporarios", batch_count, execution_start_time, running=True)
                                all_updates.clear()

        except Exception as e:
            print(f'erro: {e}')
        finally:
            driver.quit()
            if all_updates:
                final_count = len(all_updates)
                try:
                    SmartsheetClient.update_bulk(all_updates, settings.SHEET_ID_TEMPORARIOS)
                finally:
                    send_execution_mapping("temporarios", "Temporarios", final_count, execution_start_time, running=False)
            else:
                print("[dispatcher_temp] Nenhum update pendente; enviando status para API com 0 linhas.")
                send_execution_mapping("temporarios", "Temporarios", 0, execution_start_time, running=False)

if __name__ == "__main__":
    import sys
    SmartsheetDispatcher.main(int(sys.argv[1]))
