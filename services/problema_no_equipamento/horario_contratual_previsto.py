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

class HorarioContratualPrevisto:
    def __init__(self, driver, row_id, sheet_id, token, data_registro):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro

    def adjust(self):
        try:
            botao_tratar_massa = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='massa_button']"))
            )
        
            if botao_tratar_massa.get_attribute("disabled") is not None:
                SmartsheetClient.update_smartsheet("Motivo Recusa", "Escala não cadastrada", self.row_id, self.sheet_id, self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                return
            botao_tratar_massa.click()
            time.sleep(2)
            SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")
            time.sleep(2)
            campo_data_incial = self.driver.find_element(By.XPATH, "//*[@id='data_inicial']")
            campo_data_final = self.driver.find_element(By.XPATH, "//*[@id='data_final']")
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data_incial, self.data_registro)
            time.sleep(2)
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data_final, self.data_registro)
            time.sleep(2)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_id']"))
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Problema no Equipamento']"))
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='preencher_feriado']"))
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@value='Salvar']"))
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Ok']"))
            ).click()
            time.sleep(4)
            #Captura texto da notificação
            element = self.driver.switch_to.active_element
            notify = WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/main/div/div/div/div/div[1]/div/div/div[1]/span")))
            texto_notify = notify.get_attribute("innerText")
            match texto_notify:
                case "1 dias de 1 colaboradores foram preenchidos. Alterações específicas devem ser feitas no módulo de tratamento.":
                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id, self.token) 
                case "0 dias de 0 colaboradores foram preenchidos. Alterações específicas devem ser feitas no módulo de tratamento.":
                    SmartsheetClient.update_smartsheet("Motivo Recusa", '0 dias de 0 colaboradores foram preenchidos.', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                case _:
                    SmartsheetClient.update_smartsheet("Status", "Não tratado", self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet("Status", texto_notify, self.row_id, self.sheet_id, self.token)
        except:
            elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
            SmartsheetClient.update_smartsheet("Motivo Recusa", 'Ponto fechado.', self.row_id, self.sheet_id, self.token)
            SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)