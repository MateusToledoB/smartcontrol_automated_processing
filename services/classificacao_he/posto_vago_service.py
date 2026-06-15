import datetime as dt
from datetime import datetime, timedelta
import re
import time
import token

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException
)

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from infrastructure.smartsheet.smartsheet_client import SmartsheetClient
from infrastructure.notifications.teams_webhook_client import TeamsWebhookClient
from utils.selenium_utils import SeleniumUtils

from utils.file_utils import FileUtils

class PostoVago:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, id_mrh, cr_cobertura):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.id_mrh = id_mrh
        self.cr_cobertura = cr_cobertura

    def adjust(self):
        updates = []
        print(f"Validando ID MRH: {self.id_mrh}, CR Cobertura: {self.cr_cobertura}, Data Registro: {self.data_registro}")
        verify = FileUtils.validate_id_mrh(self.id_mrh, self.cr_cobertura, self.data_registro)
        print(verify)
        
        match verify:
            case "ID não encontrado":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "ID MRH não encontrado."})
                return updates
            
            case "CR não corresponde":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "CR de cobertura não corresponde ao ID MRH."})
                return updates
            
            case "Data fora do período":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Data de registro fora do período permitido."})
                return updates
            case "Aprovado":
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='hora_extra_button']"))
                    ).click()

                    SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

                    xpath_select = f"(//div[@class='body'])[1]//table//tr[td[normalize-space()='{self.data_registro}']]//select"
                    select_hora_extra = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, xpath_select))
                    )

                    try:
                        select_hora_extra.click()
                    except Exception:
                        select_hora_extra.click()

                    elemento_posto_vago = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            f"""
                            (//div[@class='body'])[1]
                            //table
                            //tr[td[normalize-space()='{self.data_registro}']]
                            //select
                            /option[normalize-space()='Posto Vago']
                            """
                        ))
                    )
                    elemento_posto_vago.click()

                    input_cr = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((
                            By.XPATH,
                            f"""
                            //td[normalize-space()='{self.data_registro}']
                            /ancestor::tr
                            /following-sibling::tr
                            //td[contains(normalize-space(),'CR')]
                            /following-sibling::td//input[@type='text']
                            """
                        ))
                    )
                    input_cr.clear()
                    input_cr.send_keys(self.cr_cobertura)
                    input_cr.click()
                    time.sleep(2)
                    input_observacao = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((
                            By.XPATH,f"//td[normalize-space()='{self.data_registro}']/preceding-sibling::td//input[contains(@name,'observacao')]"
                        ))
                    )
                    input_observacao.clear()
                    input_observacao.send_keys(self.id_mrh)
                    print('inputou o id_mrh')
                    time.sleep(2)
                    for tentativa in range(10):

                        try:

                            btn_salvar = WebDriverWait(self.driver, 20).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//*[@value='Salvar']")
                                )
                            )

                            btn_salvar.click()

                            print("salvou")
                            break

                        except (ElementClickInterceptedException, StaleElementReferenceException):

                            print(f"loader ativo - tentativa {tentativa+1}")

                            WebDriverWait(self.driver, 30).until(
                                lambda d: d.execute_script("""
                                    const el = document.getElementById('sc-loading-div');

                                    return !el || !el.classList.contains('is-active');
                                """)
                            )

                            time.sleep(1)
                    print('salvou')
                    time.sleep(1)
                    notify = WebDriverWait(self.driver, 50).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="top_pad_div"]/div/div/div[1]/span'))
                    )
                    notify = notify.get_attribute("innerText")
                    if notify == "Registros salvos com sucesso":
                        updates.append({"column": "Status", "value": "Tratado"})

                except Exception as e:
                    print(f"Erro ao processar linha {self.row_id}: {e}")
                    time.sleep(10)
                    elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "Ponto fechado."})
                    return updates

                return updates
