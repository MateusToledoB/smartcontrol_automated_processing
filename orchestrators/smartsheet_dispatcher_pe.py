from datetime import datetime, timedelta
import time

from core.settings import settings
from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from services.problema_no_equipamento.horario_contratual_previsto import HorarioContratualPrevisto
from services.problema_no_equipamento.informar_horario_realizado import InformarHorarioRealizado
from services.problema_no_equipamento.falta_abono import FaltaAbono

from utils.driver_factory import DriverFactory

class SmartsheetDispatcher:
    @staticmethod
    def main(worker_id: int, total_workers: int = 1):
        sheet, _, token, sheet_id, _ = SmartsheetClient.setup_smartsheet(settings.SHEET_ID_PROBLEMA_NO_EQUIPAMENTO)
        nome_coluna_para_indice = {coluna.title: index for index, coluna in enumerate(sheet.columns)}

        df_cr = SmartsheetClient.return_df_crs()

        if worker_id < 1 or worker_id > total_workers:
            raise ValueError(f"worker_id deve estar entre 1 e {total_workers}")

        total         = len(sheet.rows)
        base, resto   = divmod(total, total_workers)
        indice_worker = worker_id - 1
        start         = indice_worker * base + min(indice_worker, resto)
        end           = start + base + (1 if indice_worker < resto else 0)

        bloco_linhas = sheet.rows[start:end]

        driver = DriverFactory.create_edge_driver()
        all_updates = []
        try:
            for linha in bloco_linhas:
          
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
                cpf               = colaborador.split("-")[0].strip() if colaborador and "-" in colaborador else None
                cpf               = str(cpf).zfill(11) if cpf is not None else None
                if intervalo != None:
                    horas, minutos = map(int, intervalo.split(":"))
                    intervalo = timedelta(hours=horas, minutes=minutos)
                classificacao     = dados_celulas.get('Classificação da Falta', None)
                cr                = dados_celulas.get('CR', None)
                cr_number         = cr_number = str(cr[:5]).zfill(5)
                observacao        = dados_celulas.get('Observação', None)
                observacao        = "Sem justificativa" if observacao is None else observacao
                row_id            = linha.id
                linha_numero      = linha.row_number

                if status == None:
                        print(f"linha {linha_numero} - Colaborador: {colaborador} - Data: {data_registro} Classificação: {classificacao}")

                        driver.get(link1_ponto)
                        match str(classificacao).strip().lower():
                            
                            case "horário contratual previsto (problema no equipamento)":
                                service = HorarioContratualPrevisto(
                                    driver=driver,
                                    row_id=row_id,
                                    sheet_id=sheet_id,
                                    token=token,
                                    data_registro=data_registro,
                                )
                                updates = service.adjust()

                            case "problema no equipamento - informar horário realizado":
                                service = InformarHorarioRealizado(
                                    driver=driver,
                                    row_id=row_id,
                                    sheet_id=sheet_id,
                                    token=token,
                                    data_registro=data_registro,
                                    entrada=entrada,
                                    saida=saida,
                                    intervalo=intervalo,
                                )
                                updates = service.adjust()

                            case "abandono" | "atraso" | "falta" | "suspensão" | "integração cliente" | "reciclagem" | "liberado pelo cliente":
                                service = FaltaAbono(
                                    driver=driver,
                                    row_id=row_id,
                                    sheet_id=sheet_id,
                                    token=token,
                                    data_registro=data_registro,
                                    classificacao_falta_lancado=classificacao,
                                    cr_number=cr_number,
                                    df_cr=df_cr,
                                    observacao=observacao

                                )
                                updates = service.adjust()

                        if updates:
                            all_updates.append({
                                "row_id": row_id,
                                "updates": updates
                            })
                                
        except Exception as e:
            print(f'erro: {e}')
        finally:
            driver.quit()
            if all_updates:
                SmartsheetClient.update_bulk(all_updates, settings.SHEET_ID_PROBLEMA_NO_EQUIPAMENTO)

if __name__ == "__main__":
    import sys
    SmartsheetDispatcher.main(int(sys.argv[1]))
