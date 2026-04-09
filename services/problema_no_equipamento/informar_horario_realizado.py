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

class InformarHorarioRealizado:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, entrada, saida, intervalo):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.verificar_he = False
        self.entrada = entrada
        self.saida = saida
        self.intervalo = intervalo

    def adjust(self):
        try:
            if self.entrada is None or self.saida is None:
                SmartsheetClient.update_smartsheet("Motivo Recusa", "Sem entrada ou saida informadas", self.row_id, self.sheet_id, self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token) 
                
            
            self.driver.switch_to.default_content()
            
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="scroll_table_1"]/tbody/tr[3]/td[1]/a/img'))
            ).click()

            time.sleep(1)

            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )
            time.sleep(1)

            SeleniumUtils.iframe_acess(self.driver, '//*[@id="v-app-div"]/div[1]/div/div/div[2]/div/iframe')

            campo_data = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="data_jornada"]'))
            )

            self.driver.execute_script(
                "arguments[0].value = arguments[1];", 
                campo_data, 
                self.data_registro
            )

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="data_jornada"]'))
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Data da jornada :']"))
            ).click()

            time.sleep(1)

            WebDriverWait(self.driver, 200).until(
                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
            )

            time.sleep(3)
  
            horario_contratual_colaborador =  self.driver.find_element(By.XPATH,'//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")
            print(f'Horário contratual colaborador: {horario_contratual_colaborador_str}')

            if "0824" in horario_contratual_colaborador_str:
                SmartsheetClient.update_smartsheet("Motivo Recusa", 'Horista', self.row_id, self.sheet_id, self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                return

            elif horario_contratual_colaborador_str == "FOLGA":
                SmartsheetClient.update_smartsheet("Motivo Recusa", 'Dia de folga', self.row_id, self.sheet_id, self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                return
            else:
                horas = re.findall(r'(?<!CH\s)(\d{2}):(\d{2})', horario_contratual_colaborador_str)
                entrada_horario_contratual_time, saida_horario_contratual_time = SeleniumUtils.retorna_entrada_e_saida_HC(horas)
                print(f'Horario entrada HC: {entrada_horario_contratual_time}, Horário saída HC: {saida_horario_contratual_time}')
                print(f" Saida informada na planilha: {self.saida} ")

                print(f'total horas: {len(horas)}')
                if len(horas) == 2:
                    tempo_intervalo = "Sem intervalo"
                else:
                    inicio_intervalo, fim_intervalo = SeleniumUtils.extrair_intervalo(horario_contratual_colaborador_str)
                    tempo_intervalo = SeleniumUtils.calcular_tempo_intervalo(inicio_intervalo, fim_intervalo)
                    print(f"Tempo do intervalo: {tempo_intervalo}")
                    print(f'intervalo informado na planilha: {self.intervalo} ')

            trs = self.driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )
            print(f'total trs: {len(trs)}')
            
            if len(trs) > 0:
                SmartsheetClient.update_smartsheet("Motivo Recusa", 'Colaborador com batidas eletronicas', self.row_id, self.sheet_id, self.token)
                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                return
                

            saida_maior_que_hc_2h = SeleniumUtils.saida_maior_que_hc_em_2h(saida_horario_contratual_time, self.saida)
            print(f'Saída maior que HC em 2h: {saida_maior_que_hc_2h}')
            
            if self.entrada == "Preencher HC":
                self.entrada = str(entrada_horario_contratual_time.strftime("%H:%M"))
            lancamento_1 = SeleniumUtils.lancar_horario_no_sistema(self.data_registro, self.entrada, self.driver)

            if lancamento_1 == "Registro realizado com sucesso":
                if self.saida == "Preencher HC":
                    self.saida = str(saida_horario_contratual_time.strftime("%H:%M"))

                if dt.datetime.strptime(self.saida, "%H:%M") < dt.datetime.strptime(self.entrada, "%H:%M"):
                    data_registro_mais_um_dia = (
                        datetime.strptime(self.data_registro, "%d/%m/%Y")
                        + timedelta(days=1)
                    ).strftime("%d/%m/%Y")
                    lancamento_2 = SeleniumUtils.lancar_horario_no_sistema(data_registro_mais_um_dia, self.saida, self.driver)
                else:
                    lancamento_2 = SeleniumUtils.lancar_horario_no_sistema(self.data_registro, self.saida, self.driver)

                if lancamento_2 == "Registro realizado com sucesso":
                    trs = self.driver.find_elements(
                        By.XPATH,
                        '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
                    )
                    total_batidas = len(trs)
                    print(f'Total de batidas após lançamentos: {total_batidas}')
                    
                    if total_batidas == 4:
                            SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id, self.token)
                            self.verificar_he = True
                            
                    elif total_batidas == 2:
                        if self.intervalo == None:
                            SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id, self.token)
                            self.verificar_he = True
                        else:
                            (
                                data_entrada_int,
                                horario_entrada_intervalo,
                                data_saida_int,
                                horario_saida_intervalo,
                            ) = SeleniumUtils.gerar_intervalo(self.data_registro, self.entrada, self.saida, self.intervalo)
                            print(
                                "Horários de intervalo a serem lançados: "
                                f"{data_entrada_int} {horario_entrada_intervalo} - "
                                f"{data_saida_int} {horario_saida_intervalo}"
                            )

                            lancamento_intervalo_1 =SeleniumUtils.lancar_horario_no_sistema(data_entrada_int, horario_entrada_intervalo, self.driver)
                            if lancamento_intervalo_1 == "Registro realizado com sucesso":
                                lancamento_intervalo_2 = SeleniumUtils.lancar_horario_no_sistema(data_saida_int, horario_saida_intervalo, self.driver)
                                if lancamento_intervalo_2 == "Registro realizado com sucesso":
                                    SmartsheetClient.update_smartsheet("Status", "Tratado", self.row_id, self.sheet_id, self.token)
                                    self.verificar_he = True
                                    
                                else:
                                    SmartsheetClient.update_smartsheet("Motivo Recusa", f"erro: {lancamento_intervalo_2}", self.row_id, self.sheet_id, self.token)
                                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                            else:
                                SmartsheetClient.update_smartsheet("Motivo Recusa", f"erro: {lancamento_intervalo_1}", self.row_id, self.sheet_id, self.token)
                                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                    else:
                        SmartsheetClient.update_smartsheet("Motivo Recusa", "Erro no tratamento", self.row_id, self.sheet_id, self.token)
                        SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
                    
                else:       
                    SmartsheetClient.update_smartsheet("Motivo Recusa", f"erro: {lancamento_2}", self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
            else:
                SmartsheetClient.update_smartsheet("Motivo Recusa", f"erro: {lancamento_1}", self.row_id, self.sheet_id, self.token)

                SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)

            if self.verificar_he:
                try:
                    self.driver.switch_to.default_content()
                    WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.XPATH, '//*[@title="Fechar"]'))
                        ).click()

                    try:
                        elemento_hora_extra = WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.XPATH, f"//tr[.//*[normalize-space(text())='{self.data_registro}']]//*[contains(@style,'color: red')]"))
                        )
                    except:
                        return

                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[@id='hora_extra_button']"))
                    ).click()
                    print("Clicou no botão de hora extra")
                    SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")
                    print('acessou o iframe')
                    xpath_select = f"(//div[@class='body'])[1]//table//tr[td[normalize-space()='{self.data_registro}']]//select"
                    # print(xpath_select)

                    select_hora_extra = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, xpath_select))
                    )
                    
                    try:
                        select_hora_extra.click()

                    except Exception:
                        select_hora_extra.click()
                    
                    elemento_ineficiencia = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((
                            By.XPATH, 
                            f"""
                            (//div[@class='body'])[1]
                            //table
                            //tr[td[normalize-space()='{self.data_registro}']]
                            //select
                            /option[normalize-space()='Ineficiência']
                            """
                            ))
                        )
                    elemento_ineficiencia.click()

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
                    input_cr.send_keys("54648")
                    elemento_ineficiencia.click()
                    time.sleep(7)
                    WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, "//*[@value='Salvar']"))
                    ).click()
                    time.sleep(1)
                    notify = WebDriverWait(self.driver, 50).until(EC.presence_of_element_located((By.XPATH,'//*[@id="top_pad_div"]/div/div/div[1]/span')))
                    notify = notify.get_attribute("innerText")
                    # print(f'Notificação hora extra: {notify}')
                    if notify == "Registros salvos com sucesso":
                        SmartsheetClient.update_smartsheet('Motivo Recusa',f"HE classificada", self.row_id, self.sheet_id, self.token)
                    else:
                        SmartsheetClient.update_smartsheet('Motivo Recusa',f"{notify}", self.row_id, self.sheet_id, self.token)
                except Exception as e:
                    print(e)
                    SmartsheetClient.update_smartsheet('Motivo Recusa',f"Erro ao tentar classificar HE", self.row_id, self.sheet_id, self.token)
        except Exception as e:
            elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
            SmartsheetClient.update_smartsheet("Motivo Recusa", 'Ponto fechado.', self.row_id, self.sheet_id, self.token)
            SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)
            
                








