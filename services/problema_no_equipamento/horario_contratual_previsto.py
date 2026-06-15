import datetime as dt
from datetime import datetime, timedelta
import re
import time
import token

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.notifications.teams_webhook_client import TeamsWebhookClient
from utils.selenium_utils import SeleniumUtils
from utils.time_utils import TimeUtils

class HorarioContratualPrevisto:
    def __init__(self, driver, row_id, sheet_id, token, data_registro):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro

    def adjust(self):
        updates = []
        try:
            tratar = True
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="scroll_table_1"]/tbody/tr[3]/td[1]/a/img'))
            ).click()
            time.sleep(1)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            time.sleep(1)
            SeleniumUtils.iframe_acess(self.driver, '//*[@id="v-app-div"]/div[1]/div/div/div[2]/div/iframe')
            time.sleep(1)
            campo_data = self.driver.find_element(By.XPATH, '//*[@id="data_jornada"]')
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data, self.data_registro)
            time.sleep(0.2)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="data_jornada"]'))
            ).click()
            time.sleep(0.2)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Data da jornada :']"))
            ).click()
            time.sleep(2)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            time.sleep(2)

            lancamento_registrado = SeleniumUtils.verifica_lancamento(self.driver)
            
            if lancamento_registrado:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": lancamento_registrado})

            horario_contratual_colaborador = self.driver.find_element(By.XPATH, '//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")
            if horario_contratual_colaborador_str != "FOLGA":
                horas = re.findall(r'(?<!CH\s)(\d{2}):(\d{2})', horario_contratual_colaborador_str)
                entrada_horario_contratual_time, saida_horario_contratual_time = TimeUtils.retorna_entrada_e_saida_HC(horas)

            element_xpath = '//*[@id="marcacoes_jornada_div"]/table/tbody'
            element = self.driver.find_element(By.XPATH, element_xpath)
            row_count = len(element.find_elements(By.TAG_NAME, "tr"))
            total_batidas = int(row_count) - 5

            print(total_batidas)

            match total_batidas:
                case 0:
                    print('iniciando')
                    print(horario_contratual_colaborador_str)
                    if horario_contratual_colaborador_str == 'FOLGA':
                        updates.append({"column": "Motivo Recusa", "value": "Marcação em dia de folga"})
                        updates.append({"column": "Status", "value": "Não Tratado"})
                    else:
                        turno = TimeUtils.define_turno_noturno_ou_diurno(entrada_horario_contratual_time, saida_horario_contratual_time)
                        entrada = entrada_horario_contratual_time.strftime("%H:%M:%S")
                        data_escrever_entrada = self.data_registro
                        saida = saida_horario_contratual_time.strftime("%H:%M:%S")
                        if turno == 'Noturno':
                            data_registro_date = dt.datetime.strptime(self.data_registro, "%d/%m/%Y").date()
                            data_mais_um_dia = data_registro_date + dt.timedelta(days=1)
                            data_escrever_saida = data_mais_um_dia.strftime("%d/%m/%Y")
                        else:
                            data_escrever_saida = self.data_registro

                        data_escrever_saida, saida = TimeUtils.randomiza_horario(data_escrever_saida, saida)
                        data_escrever_entrada, entrada = TimeUtils.randomiza_horario(data_escrever_entrada, entrada)
                        
                        lancamento_entrada = SeleniumUtils.lancar_horario_no_sistema(data_escrever_entrada, entrada, self.driver)
                        if lancamento_entrada == "Registro realizado com sucesso":
                            lancamento_saida = SeleniumUtils.lancar_horario_no_sistema(data_escrever_saida, saida, self.driver)
                            if lancamento_saida == "Registro realizado com sucesso":
                                updates.append({"column": "Status", "value": "Tratado"})
                            else:
                                updates.append({"column": "Motivo Recusa", "value": "Erro ao lançar marcação de saída"})
                                updates.append({"column": "Status", "value": "Não Tratado"})
                        else:
                            updates.append({"column": "Motivo Recusa", "value": "Erro ao lançar marcação de entrada"})
                            updates.append({"column": "Status", "value": "Não Tratado"})

                        print(data_escrever_entrada, entrada, data_escrever_saida, saida)

                case _ :
                    updates.append({"column": "Motivo Recusa", "value": "Excesso batidas encontrado"})
                    updates.append({"column": "Status", "value": "Não Tratado"})

        except Exception:
            try:
                self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
                updates.append({"column": "Motivo Recusa", "value": "Ponto fechado."})
                updates.append({"column": "Status", "value": "Não Tratado"})
            except Exception:
                pass

        return updates
