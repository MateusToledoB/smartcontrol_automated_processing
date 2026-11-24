import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.selenium_utils import SeleniumUtils


class HorarioContratualPrevistoTemp:
    def __init__(self, driver, row_id, sheet_id, token, data_registro):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro

    def adjust(self):
        updates = []
        try:
            SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")
            botao_tratar_massa = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='massa_button']"))
            )
            if botao_tratar_massa.get_attribute("disabled") is not None:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Escala não cadastrada"})
                return updates

            botao_tratar_massa.click()

            WebDriverWait(self.driver, 20).until(
                lambda d: len(d.find_elements(By.TAG_NAME, "iframe")) > 0
            )

            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")

            self.driver.switch_to.frame(iframes[0])
            campo_data_incial = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='data_inicial']"))
            )
            campo_data_final = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='data_final']"))
            )
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data_incial, self.data_registro)
            self.driver.execute_script("arguments[0].value = arguments[1];", campo_data_final, self.data_registro)

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='motivo_id']"))
            ).click()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Problema no Equipamento']"))
            ).click()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='preencher_feriado']"))
            ).click()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[@value='Salvar']"))
            ).click()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[text()='Ok']"))
            ).click()
            time.sleep(6)

            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='alert']//div[contains(@class, 'v-alert__content')]//span[@style='font-size: 11px;']"))
            )
            notify = self.driver.find_element(By.XPATH, "//div[@role='alert']//div[contains(@class, 'v-alert__content')]//span[@style='font-size: 11px;']")
            texto_notify = notify.text

            match texto_notify:
                case "1 dias de 1 colaboradores foram preenchidos. Alterações específicas devem ser feitas no módulo de tratamento.":
                    updates.append({"column": "Status", "value": "Tratado"})
                    return updates
                case "0 dias de 0 colaboradores foram preenchidos. Alterações específicas devem ser feitas no módulo de tratamento.":
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": "0 dias de 0 colaboradores foram preenchidos."})
                    return updates
                case _:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": texto_notify})
                    return updates
        except Exception:
            try:
                self.driver.find_element(By.XPATH, "//span[@title='Fechado']")
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Ponto fechado."})
                return updates
            except Exception:
                self.driver.find_element(By.XPATH, "//*[text()='Nenhum colaborador corresponde aos filtros de pesquisa selecionados']")
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "CPF não encontrado"})
                return updates

        return updates
