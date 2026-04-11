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
from utils.time_utils import TimeUtils

class ApontamentoImparTemp:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, hora_informada):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.hora_informada = hora_informada

    def adjust(self):
        try:
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
            SeleniumUtils.iframe_acess(self.driver,'//*[@id="v-app-div"]/div[1]/div/div/div[2]/div/iframe')
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
            #Pega o texto do campo Horário contratual
            horario_contratual_colaborador =  self.driver.find_element(By.XPATH,'//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")
            if horario_contratual_colaborador_str == "FOLGA":
                pass
            else:
                horas = re.findall(r'(?<!CH\s)(\d{2}):(\d{2})', horario_contratual_colaborador_str)
                #print(horas)
                entrada_horario_contratual_time, saida_horario_contratual_time = TimeUtils.retorna_entrada_e_saida_HC(horas)
                #print(entrada_horario_contratual_time, saida_horario_contratual_time)
            element_xpath = '//*[@id="marcacoes_jornada_div"]/table/tbody'
            element = self.driver.find_element(By.XPATH, element_xpath)
            # Obtenha o número de linhas (elementos tr) dentro do corpo da tabela
            row_count = len(element.find_elements(By.TAG_NAME, "tr"))
            row_count = int(row_count)
            total_batidas = row_count - 5

            match total_batidas:
                case 1:

                    if horario_contratual_colaborador_str == 'FOLGA':
                        SmartsheetClient.update_smartsheet('Motivo Recusa', 'Marcação em dia de folga', self.row_id, self.sheet_id, self.token)
                        SmartsheetClient.update_smartsheet('Status', 'Não Tratado', self.row_id, self.sheet_id, self.token)
                    else:
                        data_marcacao = self.driver.find_element(
                            By.XPATH,
                            '//*[@id="marcacoes_jornada_div"]/table/tbody/tr[2]/td[2]'
                        ).get_attribute("innerText")

                        # converte para datetime.date
                        data_marcacao_dt = dt.datetime.strptime(data_marcacao, "%d/%m/%Y").date()

                        try:
                            hora_ajuste = self.driver.find_element(
                                By.XPATH,
                                '//*[@id="marcacoes_jornada_div"]/table/tbody/tr[2]/td[3]'
                            ).get_attribute("innerText")

                            # converte direto para datetime.time
                            hora_batidada_pelo_colaborador_time = dt.datetime.strptime(hora_ajuste, '%H:%M').time()

                        except Exception as e: 
                            hora_batidada_pelo_colaborador_time = dt.datetime.strptime("00:00", '%H:%M').time()

                        #print(f'hora batida pela pessoa: {hora_batidada_pelo_colaborador_time}')
                        turno = TimeUtils.define_turno_noturno_ou_diurno(entrada_horario_contratual_time, saida_horario_contratual_time)
                        #print(f'turno da pessoa: {turno}')

                        horario_pendente = TimeUtils.calcula_diferenca_entrada_saida(data_marcacao_dt, hora_batidada_pelo_colaborador_time, self.data_registro, entrada_horario_contratual_time, saida_horario_contratual_time, turno)
                        #print(f'o horario pendente é: {horario_pendente}')

                        if self.hora_informada == 'Preencher HC':
                            if horario_pendente == 'Saida':
                                horario_escrever = saida_horario_contratual_time.strftime("%H:%M:%S")  # "08:00:00"
                                if turno == 'Noturno':
                                    data_registro_date = dt.datetime.strptime(self.data_registro, "%d/%m/%Y").date()
                                    data_mais_um_dia = data_registro_date + dt.timedelta(days=1)
                                    data_mais_um_dia_str = data_mais_um_dia.strftime("%d/%m/%Y")
                                    data_escrever = data_mais_um_dia_str
                                else:
                                    data_escrever = self.data_registro
                                
                            else:
                                horario_escrever = entrada_horario_contratual_time.strftime("%H:%M:%S")  # "08:00:00"
                                data_escrever = self.data_registro
                                
                        else:
                            if horario_pendente == 'Saida':
                                pode_lancar_horario_informado = TimeUtils.verifica_proximidade(saida_horario_contratual_time, self.hora_informada)
                            elif horario_pendente == "Entrada":
                                #print('verificando a proximidade')
                                pode_lancar_horario_informado = TimeUtils.verifica_proximidade(entrada_horario_contratual_time, self.hora_informada)

                            if pode_lancar_horario_informado == True:
                                # print(f'Pode lançar o horário informado: {self.hora_informada}')
                                horario_escrever = self.hora_informada.strftime("%H:%M:%S")  # "08:00:00"
                                if turno == 'Noturno entrada 00' or turno == 'Diurno':
                                    data_escrever = self.data_registro
                                else:
                                    if horario_pendente == "Saida":
                                        data_registro_date = dt.datetime.strptime(self.data_registro, "%d/%m/%Y").date()
                                        data_mais_um_dia = data_registro_date + dt.timedelta(days=1)
                                        data_mais_um_dia_str = data_mais_um_dia.strftime("%d/%m/%Y")
                                        data_escrever = data_mais_um_dia_str
                                    else:
                                        data_escrever = self.data_registro
                            else:
                                SmartsheetClient.update_smartsheet('Motivo Recusa',"Divergência no horário informado",self.row_id,self.sheet_id, self.token)
                                SmartsheetClient.update_smartsheet('Status', 'Não tratado',self.row_id,self.sheet_id, self.token)
                                tratar = False
                                
                        if tratar == True:
                            # print(f'A data a ser lançada é: {data_escrever}')
                            data_marcacao = self.driver.find_element(By.XPATH, '//*[@id="data_marcacao"]')
                            self.driver.execute_script("arguments[0].value = arguments[1];", data_marcacao, data_escrever)
                            time.sleep(1)
                            
                            # print(f'A hora a ser lançada é: {horario_escrever}')
                            campo_hora_marcacao = WebDriverWait(self.driver, 10).until(
                                EC.visibility_of_element_located((By.XPATH, "//*[@id='hora_marcacao']"))
                            )
                            campo_hora_marcacao.clear()
                            campo_hora_marcacao.send_keys(horario_escrever)
                            time.sleep(1)
                            WebDriverWait(self.driver, 200).until(
                                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
                            )
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//*[@id='motivo_marcacao']"))
                            ).click()
                            time.sleep(1)
                            WebDriverWait(self.driver, 200).until(
                                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
                            )
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//*[text()='Ajustes']"))
                            ).click()
                            time.sleep(1)
                            WebDriverWait(self.driver, 200).until(
                                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
                            )
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "(//*[@title='Salvar'])[3]"))
                            ).click()
                            time.sleep(2)
                            WebDriverWait(self.driver, 200).until(
                                EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
                            )
                            time.sleep(2)
                            notify = WebDriverWait(self.driver, 50).until(EC.presence_of_element_located((By.XPATH,'//*[@id="top_pad_div"]/div/div/div[1]/span')))
                            notify = notify.get_attribute("innerText")
                            #print(notify)

                            match notify:
                                case "Registro realizado com sucesso":
                                    SmartsheetClient.update_smartsheet('Status', 'Tratado',self.row_id,self.sheet_id, self.token)
                                    
                                    
                                    self.driver.switch_to.default_content()
                                    elemento = WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, '//*[@title="Fechar"]'))
                                    )
                                    self.driver.execute_script("arguments[0].click();", elemento)

                                    try:
                                        elemento_hora_extra = WebDriverWait(self.driver, 10).until(
                                            EC.visibility_of_element_located((By.XPATH, f"//tr[.//*[normalize-space(text())='{self.data_registro}']]//*[contains(@style,'color: red')]"))
                                        )

                                        WebDriverWait(self.driver, 5).until(
                                            EC.element_to_be_clickable((By.XPATH, "//*[@id='hora_extra_button']"))
                                        ).click()

                                        SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")
                                        
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
                                            SmartsheetClient.update_smartsheet('Motivo Recusa',f"{horario_escrever} - {data_escrever} - HE classificada",self.row_id,self.sheet_id, self.token)

                                    except Exception as e:
                                        SmartsheetClient.update_smartsheet('Motivo Recusa',f"{horario_escrever} - {data_escrever}",self.row_id,self.sheet_id, self.token)
                                        return

                                case "A diferença entre é menor do que duas horas.":        
                                    SmartsheetClient.update_smartsheet('Motivo Recusa',"Horário muito próximo ao registro original.",self.row_id,self.sheet_id, self.token)
                                    SmartsheetClient.update_smartsheet('Status', 'Não tratado',self.row_id,self.sheet_id, self.token)
                                    
                                case "Registro nÃ£o pode cruzar a jornada realizada seguinte":
                                    SmartsheetClient.update_smartsheet('Motivo Recusa',"Possível erro na escala.",self.row_id,self.sheet_id, self.token)
                                    SmartsheetClient.update_smartsheet('Status', 'Não tratado',self.row_id,self.sheet_id, self.token)

                                case "Registro nÃ£o pode cruzar a jornada realizada anterior":
                                    SmartsheetClient.update_smartsheet('Motivo Recusa',"Divergencia SmartControl",self.row_id,self.sheet_id, self.token)
                                    SmartsheetClient.update_smartsheet('Status', 'Não tratado',self.row_id,self.sheet_id, self.token)

                                case "HorÃ¡rio de registro jÃ¡ realizado":
                                    SmartsheetClient.update_smartsheet('Motivo Recusa',"Horário de registro já realizado",self.row_id,self.sheet_id, self.token)
                                    SmartsheetClient.update_smartsheet('Status', 'Não tratado',self.row_id,self.sheet_id, self.token)
                            
                case 0:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '0 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Não Tratado', self.row_id, self.sheet_id, self.token)
                case 2:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '2 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Tratado', self.row_id, self.sheet_id, self.token)
                case 3:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '3 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Não Tratado', self.row_id, self.sheet_id, self.token)
                case 4:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '4 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Tratado', self.row_id, self.sheet_id, self.token)
                case 5:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '5 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Não Tratado', self.row_id, self.sheet_id, self.token)
                case 6:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', '6 batidas encontradas', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Tratado', self.row_id, self.sheet_id, self.token)
                case _ if total_batidas >= 7:
                    SmartsheetClient.update_smartsheet('Motivo Recusa', 'Excesso batidas encontrado', self.row_id, self.sheet_id, self.token)
                    SmartsheetClient.update_smartsheet('Status', 'Não Tratado', self.row_id, self.sheet_id, self.token)
        except Exception as e:
            elemento_ponto_fechado = self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
            SmartsheetClient.update_smartsheet("Motivo Recusa", 'Ponto fechado.', self.row_id, self.sheet_id, self.token)
            SmartsheetClient.update_smartsheet("Status", "Não Tratado", self.row_id, self.sheet_id, self.token)

