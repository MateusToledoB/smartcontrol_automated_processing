import datetime as dt
from datetime import datetime, timedelta
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.notifications.teams_webhook_client import TeamsWebhookClient
from services.treatment_rules import TreatmentRules
from services.treatment_rules import TreatmentRules
from utils.selenium_utils import SeleniumUtils

class FaltaDescontoBH:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, classificacao_falta_lancado, cr_number, df_cr, observacao):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.classificacao_falta_lancado = classificacao_falta_lancado 
        self.cr_number = cr_number
        self.df_cr = df_cr
        self.observacao = observacao

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
        updates = []
        try:
            response_change_rule_bh = TreatmentRules.change_rule_bh(self.driver, self.data_registro, updates)

            if response_change_rule_bh:
                return response_change_rule_bh

            classificacao_fata = FaltaDescontoBH.dict_classificacao_fata[self.classificacao_falta_lancado]
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
                    updates.append({"column": "Status", "value": "Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": lancamento_registrado})
                else:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Lançamento Justificativa divergente"})
                fim = time.time()
                return updates
            else:
                pass

            horario_contratual_colaborador     =  self.driver.find_element(By.XPATH,'//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")

            if horario_contratual_colaborador_str == "FOLGA":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Dia de folga"})
                return updates
            
            elemento_tempo_falta = self.driver.find_element(By.XPATH, "//font[@color='red']")
                
            texto_tempo_falta = elemento_tempo_falta.text.strip() 
            # #print(f'Tempo de falta: {texto_tempo_falta}')
            if texto_tempo_falta == '':
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Sem tempo de falta gerado"})
                return updates
            
            tempo_falta_obj = dt.datetime.strptime(texto_tempo_falta, "%H:%M").time()
            tempo_limite = dt.time(3, 0)

            if tempo_falta_obj > tempo_limite:
                lancar_observacao_falta = True
            else:
                lancar_observacao_falta = False

            trs = self.driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )
            total_batidas = len(trs)

            if classificacao_fata == "Hora Justificada Empresa":
                if total_batidas  == 1:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Batida impar"})
                    return updates
                elif total_batidas  == 0:
                    if SmartsheetClient.return_validation_cr(self.df_cr, self.cr_number, "dia") == "NÃO":
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "CR não autorizado"})
                        return updates

                    time.sleep(3)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']"))
                    ).click()
   
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//*[@id='motivo_abonar']//*[normalize-space(text())='Dia Justificado Empresa']"))
                    ).click()
           
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']/following::*[@title='Salvar'][1]"))
                    ).click()
                    time.sleep(3)

                    if lancar_observacao_falta:    
                        response_records_observation = TreatmentRules.records_observation(self.driver, self.observacao, self.data_registro, updates)
                        if response_records_observation:
                            return response_records_observation
                        
                    updates.append({"column": "Status", "value": "Tratado"})
                    return updates
                elif total_batidas > 4:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Mais de 4 batidas"})
                    return updates
                
                elif total_batidas == 2:
                    if SmartsheetClient.return_validation_cr(self.df_cr, self.cr_number, "hora") == "NÃO":
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "CR não autorizado"})
                        return updates
                    
                    # print(f'Lancar obs: {lancar_observacao_falta}')
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
                  
                    lancamento_intervalo = TreatmentRules.check_interval_launch(self.driver, self.data_registro)

                    if lancamento_intervalo == False:
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "Erro ao lançar intervalo para ch > 6h"})
                        return updates
                    
                    updates.append({"column": "Status", "value": "Tratado"})

                    if lancar_observacao_falta:    
                        response_records_observation = TreatmentRules.records_observation(self.driver, self.observacao, self.data_registro, updates)
                        if response_records_observation:
                            return response_records_observation
                        
                    return updates  
            match total_batidas:
                case 0 | 2 | 4:
                    if classificacao_fata == "Integração Cliente" and total_batidas > 0:
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "Batida realizada em integração"})
                        return updates
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
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "Não foi possivel lançar a justificativa"})
                        return updates
                    time.sleep(1)
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_abonar']/following::*[@title='Salvar'][1]"))
                    ).click()
                    time.sleep(3)

                    if lancar_observacao_falta:    
                        response_records_observation = TreatmentRules.records_observation(self.driver, self.observacao, self.data_registro, updates)
                        if response_records_observation:
                            return response_records_observation
                        
                    updates.append({"column": "Status", "value": "Tratado"})
                    return updates

                case 1 | 3 | 5:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Batida impar."})
                    return updates

                case 6 | 7 | 8:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Excesso de batidas"})
                    return updates
                
        except Exception as e:
                elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Ponto fechado."})
                return updates

        return updates





