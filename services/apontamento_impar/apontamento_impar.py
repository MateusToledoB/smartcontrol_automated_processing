import datetime as dt
from datetime import datetime, timedelta
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.selenium_utils import SeleniumUtils
from utils.time_utils import TimeUtils


class ApontamentoImpar:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, hora_informada):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.hora_informada = hora_informada

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

            match total_batidas:
                case 1:
                    if horario_contratual_colaborador_str == 'FOLGA':
                        updates.append({"column": "Motivo Recusa", "value": "Marcação em dia de folga"})
                        updates.append({"column": "Status", "value": "Não Tratado"})
                    else:
                        data_marcacao = self.driver.find_element(
                            By.XPATH,
                            '//*[@id="marcacoes_jornada_div"]/table/tbody/tr[2]/td[2]'
                        ).get_attribute("innerText")

                        data_marcacao_dt = dt.datetime.strptime(data_marcacao, "%d/%m/%Y").date()

                        try:
                            hora_ajuste = self.driver.find_element(
                                By.XPATH,
                                '//*[@id="marcacoes_jornada_div"]/table/tbody/tr[2]/td[3]'
                            ).get_attribute("innerText")
                            hora_batidada_pelo_colaborador_time = dt.datetime.strptime(hora_ajuste, '%H:%M').time()
                        except Exception:
                            hora_batidada_pelo_colaborador_time = dt.datetime.strptime("00:00", '%H:%M').time()

                        turno = TimeUtils.define_turno_noturno_ou_diurno(entrada_horario_contratual_time, saida_horario_contratual_time)
                        horario_pendente = TimeUtils.calcula_diferenca_entrada_saida(
                            data_marcacao_dt,
                            hora_batidada_pelo_colaborador_time,
                            self.data_registro,
                            entrada_horario_contratual_time,
                            saida_horario_contratual_time,
                            turno
                        )

                        if self.hora_informada == 'Preencher HC':
                            if horario_pendente == 'Saida':
                                horario_escrever = saida_horario_contratual_time.strftime("%H:%M:%S")
                                if turno == 'Noturno':
                                    data_registro_date = dt.datetime.strptime(self.data_registro, "%d/%m/%Y").date()
                                    data_mais_um_dia = data_registro_date + dt.timedelta(days=1)
                                    data_escrever = data_mais_um_dia.strftime("%d/%m/%Y")
                                else:
                                    data_escrever = self.data_registro
                            else:
                                horario_escrever = entrada_horario_contratual_time.strftime("%H:%M:%S")
                                data_escrever = self.data_registro
                        else:
                            if horario_pendente == 'Saida':
                                pode_lancar_horario_informado = TimeUtils.verifica_proximidade(saida_horario_contratual_time, self.hora_informada)
                            elif horario_pendente == "Entrada":
                                pode_lancar_horario_informado = TimeUtils.verifica_proximidade(entrada_horario_contratual_time, self.hora_informada)
                            else:
                                pode_lancar_horario_informado = False

                            if pode_lancar_horario_informado:
                                horario_escrever = self.hora_informada.strftime("%H:%M:%S")
                                if turno == 'Noturno entrada 00' or turno == 'Diurno':
                                    data_escrever = self.data_registro
                                else:
                                    if horario_pendente == "Saida":
                                        data_registro_date = dt.datetime.strptime(self.data_registro, "%d/%m/%Y").date()
                                        data_mais_um_dia = data_registro_date + dt.timedelta(days=1)
                                        data_escrever = data_mais_um_dia.strftime("%d/%m/%Y")
                                    else:
                                        data_escrever = self.data_registro
                            else:
                                updates.append({"column": "Motivo Recusa", "value": "Divergência no horário informado"})
                                updates.append({"column": "Status", "value": "Não tratado"})
                                tratar = False

                        if tratar:
                            data_marcacao = self.driver.find_element(By.XPATH, '//*[@id="data_marcacao"]')
                            self.driver.execute_script("arguments[0].value = arguments[1];", data_marcacao, data_escrever)
                            time.sleep(1)

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
                            notify = WebDriverWait(self.driver, 50).until(
                                EC.presence_of_element_located((By.XPATH, '//*[@id="top_pad_div"]/div/div/div[1]/span'))
                            )
                            notify = notify.get_attribute("innerText")
                            
                            match notify:
                                case "Registro realizado com sucesso":
                                    updates.append({"column": "Status", "value": "Tratado"})

                                    self.driver.switch_to.default_content()
                                    elemento = WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, '//*[@title="Fechar"]'))
                                    )
                                    self.driver.execute_script("arguments[0].click();", elemento)

                                    try:
                                        WebDriverWait(self.driver, 5).until(
                                            EC.visibility_of_element_located((By.XPATH, f"//tr[.//*[normalize-space(text())='{self.data_registro}']]//*[contains(@style,'color: red')]"))
                                        )

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
                                        notify = WebDriverWait(self.driver, 50).until(
                                            EC.presence_of_element_located((By.XPATH, '//*[@id="top_pad_div"]/div/div/div[1]/span'))
                                        )
                                        notify = notify.get_attribute("innerText")
                                        if notify == "Registros salvos com sucesso":
                                            updates.append({"column": "Motivo Recusa", "value": f"{horario_escrever} - {data_escrever} - HE classificada"})

                                    except Exception:
                                        updates.append({"column": "Motivo Recusa", "value": f"{horario_escrever} - {data_escrever}"})

                                case "A diferença entre é menor do que duas horas.":
                                    updates.append({"column": "Motivo Recusa", "value": "Horário muito próximo ao registro original."})
                                    updates.append({"column": "Status", "value": "Não tratado"})

                                case "Registro nÃƒÂ£o pode cruzar a jornada realizada seguinte":
                                    updates.append({"column": "Motivo Recusa", "value": "Possível erro na escala."})
                                    updates.append({"column": "Status", "value": "Não tratado"})

                                case "Registro nÃƒÂ£o pode cruzar a jornada realizada anterior":
                                    updates.append({"column": "Motivo Recusa", "value": "Divergencia SmartControl"})
                                    updates.append({"column": "Status", "value": "Não tratado"})

                                case "HorÃƒÂ¡rio de registro jÃƒÂ¡ realizado":
                                    updates.append({"column": "Motivo Recusa", "value": "Horário de registro já realizado"})
                                    updates.append({"column": "Status", "value": "Não tratado"})
                                
                                case "HorÃ¡rio de registro jÃ¡ realizado":
                                    updates.append({"column": "Motivo Recusa", "value": "Horário de registro já realizado"})
                                    updates.append({"column": "Status", "value": "Não tratado"})
                                
                                case _:
                                    updates.append({"column": "Motivo Recusa", "value": {notify}})
                                    updates.append({"column": "Status", "value": "Não tratado"})


                case 0:
                    updates.append({"column": "Motivo Recusa", "value": "0 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Não Tratado"})
                case 2:
                    updates.append({"column": "Motivo Recusa", "value": "2 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Tratado"})
                case 3:
                    updates.append({"column": "Motivo Recusa", "value": "3 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Não Tratado"})
                case 4:
                    updates.append({"column": "Motivo Recusa", "value": "4 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Tratado"})
                case 5:
                    updates.append({"column": "Motivo Recusa", "value": "5 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Não Tratado"})
                case 6:
                    updates.append({"column": "Motivo Recusa", "value": "6 batidas encontradas"})
                    updates.append({"column": "Status", "value": "Tratado"})
                case _ if total_batidas >= 7:
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

