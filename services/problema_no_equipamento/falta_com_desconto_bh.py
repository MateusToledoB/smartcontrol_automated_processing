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
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Lançamento Justificativa divergente"})
                
                return updates
           
            horario_contratual_colaborador     =  self.driver.find_element(By.XPATH,'//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")

            if horario_contratual_colaborador_str == "FOLGA":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Dia de folga"})
                return updates

            trs = self.driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )

            total_batidas = len(trs)

            match total_batidas:
                case 0 | 2 | 4:
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

                    self.driver.switch_to.default_content()

                    elemento = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@title="Fechar"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", elemento)
                    
                    time.sleep(2)

                    banco_horas = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@value='Tratar banco de horas']"))
                    )

                    self.driver.execute_script("arguments[0].click();", banco_horas)

                    SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

                    radio_xpath = (
                        f"//td[contains(normalize-space(), '{self.data_registro}')]"
                        f"/parent::tr//input[@type='radio']"
                    )

                    checkbox_xpath = (
                        f"//td[contains(normalize-space(), '{self.data_registro}')]"
                        f"/parent::tr//input[@type='checkbox']"
                    )

                    # pega os radios
                    radios = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_all_elements_located((By.XPATH, radio_xpath))
                    )

                    desc_element = radios[0]

                    # verifica se está desabilitado
                    if not desc_element.is_enabled():

                        checkboxes = WebDriverWait(self.driver, 20).until(
                            EC.presence_of_all_elements_located((By.XPATH, checkbox_xpath))
                        )

                        self.driver.execute_script(
                            "arguments[0].click();",
                            checkboxes[0]
                        )

                    # clica no radio
                    self.driver.execute_script(
                        "arguments[0].click();",
                        desc_element
                    )

                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//button[text()='Salvar']"))
                    ).click()

                    time.sleep(2)

                    notify_mudanca_regra = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//span[@style='font-size: 11px;']"))
                    )
                    
                    texto_notify = notify_mudanca_regra.text if notify_mudanca_regra else ""
                    
                    match texto_notify:
                        case "Tratamento de banco de horas salvo com sucesso":
                            updates.append({"column": "Status", "value": "Tratado"})
                        
                        case _:
                            updates.append({"column": "Status", "value": "Não Tratado"})
                            updates.append({"column": "Motivo Recusa", "value": {texto_notify}})

                    
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





