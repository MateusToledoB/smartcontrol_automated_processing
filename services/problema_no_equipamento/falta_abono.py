import datetime as dt
from datetime import datetime, timedelta
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.notifications.teams_webhook_client import TeamsWebhookClient
from utils.selenium_utils import SeleniumUtils

class FaltaAbono:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, classificacao_falta_lancado):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.classificacao_falta_lancado = classificacao_falta_lancado 

    dict_classificacao_fata = {
        "Abandono": "Abandono",
        "Atraso": "Atrasos",
        "Falta": "Falta",
        "Suspensão": "Suspensão",
        "Integração Cliente": "Integração Cliente",
        "Reciclagem": "Treinamento / Reciclagem",
        "Liberado pelo Cliente": "Hora Justificada Empresa"
    }

    def adjust(self):
        try:
            classificacao_fata = FaltaAbono.dict_classificacao_fata[self.classificacao_falta_lancado]
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="scroll_table_1"]/tbody/tr[3]/td[1]/a/img'))
            ).click()
            time.sleep(1)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.ID, "sc-loading-div"))
            )
            time.sleep(1)  
            SeleniumUtils.iframe_acess(self.driver,'//*[@id="v-app-div"]/div[1]/div/div/div[2]/div/iframe')
            time.sleep(1)       
            campo_data = self.driver.find_element(By.XPATH, '//*[@id="data_jornada"]')
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data, self.data_registro)
            time.sleep(0.2)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="data_jornada"]'))
            ).click()
            time.sleep(0.2)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Data da jornada :']"))
            ).click()
            time.sleep(2)
            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.ID, "sc-loading-div"))
            )
            time.sleep(1)

            lancamento_registrado = SeleniumUtils.verifica_lancamento(self.driver)
            
            if lancamento_registrado:
                if lancamento_registrado == classificacao_fata:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", lancamento_registrado, self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id,self.token)
                else:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", "Lançamento Justificativa divergente", self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                fim = time.time()
                return
            else:
                pass

            horario_contratual_colaborador     =  self.driver.find_element(By.XPATH,'//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")

            if horario_contratual_colaborador_str == "FOLGA":
                SmartsheetClient.update_smartsheet("Motivo Recusa", "Dia de folga", self.row_id, self.sheet_id,self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                return

            trs = self.driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )
            total_batidas = len(trs)

            if classificacao_fata == "Hora Justificada Empresa":
                if total_batidas  == 1:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Batida impar', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                    return
                elif total_batidas  == 0:
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']"))
                    ).click()
                    time.sleep(1)  
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//*[@id='motivo_abonar']//*[normalize-space(text())='Dia Justificado Empresa']"))
                    ).click()
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']/following::*[@title='Salvar'][1]"))
                    ).click()
                    time.sleep(3)
                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id,self.token)
                    return
                elif total_batidas > 4:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Mais de 4 batidas', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                    return

                elemento_tempo_falta = self.driver.find_element(By.XPATH, "//font[@color='red']")
                
                texto_tempo_falta = elemento_tempo_falta.text.strip() 
                # #print(f'Tempo de falta: {texto_tempo_falta}')
                if texto_tempo_falta == '':
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Sem tempo de falta gerado', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                    return
                tempo_falta_obj = dt.datetime.strptime(texto_tempo_falta, "%H:%M").time()
                tempo_limite = dt.time(3, 0)

                if tempo_falta_obj > tempo_limite:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Falta maior que 3H', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                    return
                elif total_batidas == 2:
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']"))
                    ).click()
                    time.sleep(1)  
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//*[@id='motivo_abonar']//*[normalize-space(text())='{classificacao_fata}']"))
                    ).click()
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']/following::*[@title='Salvar'][1]"))
                    ).click()
                    time.sleep(3)
                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id,self.token)
                    return
            match total_batidas:
                case 0 | 2 | 4:
                    if classificacao_fata == "Integração Cliente" and total_batidas > 0:
                        SmartsheetClient.update_smartsheet("Motivo Recusa", 'Batida realizada em integração', self.row_id, self.sheet_id,self.token)
                        SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                        return
                    if classificacao_fata in ["Suspensão", "Falta", "Atrasos", "Abandono"]:
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and normalize-space(following-sibling::text()[1])='Dispensa / suspensão']"))
                            ).click()
                        except:
                            self.driver.execute_script("document.documentElement.scrollTop = document.documentElement.scrollHeight")
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and normalize-space(following-sibling::text()[1])='Dispensa / suspensão']"))
                            ).click()
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']"))
                    ).click()
                    time.sleep(1)  
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, f"//*[@id='motivo_abonar']//*[normalize-space(text())='{classificacao_fata}']"))
                        ).click()
                    except Exception as e:
                        SmartsheetClient.update_smartsheet("Motivo Recusa", 'Não foi possivel lançar a justificativa', self.row_id, self.sheet_id,self.token)
                        SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                        return
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']/following::*[@title='Salvar'][1]"))
                    ).click()
                    time.sleep(3)
                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id,self.token)

                case 1 | 3 | 5:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Batida impar.', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)

                case 6 | 7 | 8:
                    SmartsheetClient.update_smartsheet("Motivo Recusa", 'Excesso de batidas', self.row_id, self.sheet_id,self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)

        except Exception as e:
                #print(e)
                elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
                SmartsheetClient.update_smartsheet("Motivo Recusa", 'Ponto fechado.', self.row_id, self.sheet_id,self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id,self.token)
                return





