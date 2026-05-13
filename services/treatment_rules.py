import datetime as dt
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime, timedelta
from core.settings import settings
from utils.selenium_utils import SeleniumUtils

class TreatmentRules:
    @staticmethod
    def check_interval_launch(driver, data_registro):
        carga_horaria = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[text()=' Carga horária : ']/following-sibling::td[1]"))
        )

        tempo_carga_horaria = str(carga_horaria.text)   
        tempo_carga_horaria_time = datetime.strptime(tempo_carga_horaria, "%H:%M")

        if tempo_carga_horaria_time > datetime.strptime("06:00", "%H:%M"):
            trs = driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )

            # Extrai o texto do terceiro TD de cada TR
            batida_1 = trs[0].find_elements(By.TAG_NAME, "td")[2].text
            batida_2 = trs[1].find_elements(By.TAG_NAME, "td")[2].text

            (
                data_entrada_int,
                horario_entrada_intervalo,
                data_saida_int,
                horario_saida_intervalo,
            ) = SeleniumUtils.gerar_intervalo(data_registro, batida_1, batida_2, timedelta(hours=1))

            lancamento_intervalo_1 =SeleniumUtils.lancar_horario_no_sistema(data_entrada_int, horario_entrada_intervalo, driver)

            if lancamento_intervalo_1 == "Registro realizado com sucesso":
                lancamento_intervalo_2 = SeleniumUtils.lancar_horario_no_sistema(data_saida_int, horario_saida_intervalo, driver)

                if lancamento_intervalo_2 == "Registro realizado com sucesso":
                    return True
                else:
                    return False
            else:
                return False     
            
    @staticmethod
    def change_rule_bh(driver, data_registro, updates):
        try:
            banco_horas = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Tratar banco de horas']"))
            )

            driver.execute_script("arguments[0].click();", banco_horas)

            SeleniumUtils.iframe_acess(driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

            radio_xpath = (
                f"//td[contains(normalize-space(), '{data_registro}')]"
                f"/parent::tr//input[@type='radio']"
            )

            checkbox_xpath = (
                f"//td[contains(normalize-space(), '{data_registro}')]"
                f"/parent::tr//input[@type='checkbox']"
            )

            # pega os radios
            radios = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, radio_xpath))
            )

            desc_element = radios[0]

            # verifica se está desabilitado
            if not desc_element.is_enabled():

                checkboxes = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, checkbox_xpath))
                )

                driver.execute_script(
                    "arguments[0].click();",
                    checkboxes[0]
                )

            # clica no radio
            driver.execute_script(
                "arguments[0].click();",
                desc_element
            )

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//button[text()='Salvar']"))
            ).click()

            time.sleep(2)

            notify_mudanca_regra = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//span[@style='font-size: 11px;']"))
            )
            
            texto_notify = notify_mudanca_regra.text if notify_mudanca_regra else ""
            
            match texto_notify:
                case "Tratamento de banco de horas salvo com sucesso":
                    driver.switch_to.default_content()
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@title='Fechar']"))
                    ).click()
                    time.sleep(1)
                case _:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": texto_notify})
                    return updates
        except:
            updates.append({"column": "Status", "value": "Não Tratado"})
            updates.append({"column": "Motivo Recusa", "value": "Não foi possivel alterar a regra"})
            return updates

    @staticmethod
    def change_rule_bh_temp(driver, data_registro, updates):
        try:
            banco_horas = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Tratar banco de horas']"))
            )

            driver.execute_script("arguments[0].click();", banco_horas)

            SeleniumUtils.iframe_acess(driver, "/html/body/div[2]/div/div[1]/div/div/div[2]/div/iframe")

            radio_xpath = (
                f"//td[contains(normalize-space(), '{data_registro}')]"
                f"/parent::tr//input[@type='radio']"
            )

            checkbox_xpath = (
                f"//td[contains(normalize-space(), '{data_registro}')]"
                f"/parent::tr//input[@type='checkbox']"
            )

            # pega os radios
            radios = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, radio_xpath))
            )

            desc_element = radios[0]

            # verifica se está desabilitado
            if not desc_element.is_enabled():

                checkboxes = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, checkbox_xpath))
                )

                driver.execute_script(
                    "arguments[0].click();",
                    checkboxes[0]
                )

            # clica no radio
            driver.execute_script(
                "arguments[0].click();",
                desc_element
            )

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//button[text()='Salvar']"))
            ).click()

            time.sleep(2)

            notify_mudanca_regra = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//span[@style='font-size: 11px;']"))
            )
            
            texto_notify = notify_mudanca_regra.text if notify_mudanca_regra else ""

            match texto_notify:
                case "Tratamento de banco de horas salvo com sucesso":
                    driver.switch_to.default_content()
                    SeleniumUtils.iframe_acess(driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@title='Fechar']"))
                    ).click()
                    time.sleep(1)
                    
                case _:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": {texto_notify}})
                    return updates
        except:
            updates.append({"column": "Status", "value": "Não Tratado"})
            updates.append({"column": "Motivo Recusa", "value": "Não foi possivel alterar a regra"})
            return updates
        


            
            