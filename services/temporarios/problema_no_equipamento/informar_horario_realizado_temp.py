import datetime as dt
from datetime import datetime, timedelta
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.selenium_utils import SeleniumUtils


class InformarHorarioRealizadoTemp:
    def __init__(self, driver, row_id, sheet_id, token, data_registro, entrada, saida, intervalo):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro
        self.entrada = entrada
        self.saida = saida
        self.intervalo = intervalo

    def adjust(self):
        updates = []
        try:
            if self.entrada is None or self.saida is None:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Sem entrada ou saida informadas"})
                return updates

            SeleniumUtils.iframe_acess(self.driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@title='Editar']"))
            ).click()

            time.sleep(2)

            SeleniumUtils.iframe_acess(self.driver, "/html/body/div[2]/div/div[1]/div/div/div[2]/div/iframe")

            horario_contratual_colaborador = self.driver.find_element(By.XPATH, '//*[@selected="selected"]')
            horario_contratual_colaborador_str = horario_contratual_colaborador.get_attribute("innerText")
            # print(f"Horário contratual colaborador: {horario_contratual_colaborador_str}")

            if "0824" in horario_contratual_colaborador_str:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Horista"})
                return updates
            elif horario_contratual_colaborador_str == "FOLGA":
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Dia de folga"})
                return updates
            else:
                horas = re.findall(r"(?<!CH\s)(\d{2}):(\d{2})", horario_contratual_colaborador_str)
                entrada_horario_contratual_time, saida_horario_contratual_time = SeleniumUtils.retorna_entrada_e_saida_HC(horas)

                if len(horas) == 2:
                    tempo_intervalo = "Sem intervalo"
                else:
                    inicio_intervalo, fim_intervalo = SeleniumUtils.extrair_intervalo(horario_contratual_colaborador_str)
                    tempo_intervalo = SeleniumUtils.calcular_tempo_intervalo(inicio_intervalo, fim_intervalo)

            trs = self.driver.find_elements(
                By.XPATH,
                '//td[normalize-space()="Incluído"]/ancestor::tr/following-sibling::tr[following-sibling::tr/td[normalize-space()="Carga horária :"]]'
            )

            if len(trs) > 0:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Colaborador com batidas eletronicas"})
                return updates

            saida_maior_que_hc_2h = SeleniumUtils.saida_maior_que_hc_em_2h(saida_horario_contratual_time, self.saida)

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

                    if total_batidas == 4:
                        self.verificar_he = True
                        updates.append({"column": "Status", "value": "Tratado"})
                        return updates

                    elif total_batidas == 2:
                        if self.intervalo is None:
                            self.verificar_he = True
                            updates.append({"column": "Status", "value": "Tratado"})
                            return updates
                        else:
                            (
                                data_entrada_int,
                                horario_entrada_intervalo,
                                data_saida_int,
                                horario_saida_intervalo,
                            ) = SeleniumUtils.gerar_intervalo(self.data_registro, self.entrada, self.saida, self.intervalo)

                            lancamento_intervalo_1 = SeleniumUtils.lancar_horario_no_sistema(data_entrada_int, horario_entrada_intervalo, self.driver)
                            if lancamento_intervalo_1 == "Registro realizado com sucesso":
                                lancamento_intervalo_2 = SeleniumUtils.lancar_horario_no_sistema(data_saida_int, horario_saida_intervalo, self.driver)
                                if lancamento_intervalo_2 == "Registro realizado com sucesso":
                                    self.verificar_he = True
                                    updates.append({"column": "Status", "value": "Tratado"})
                                    return updates

                                updates.append({"column": "Status", "value": "Não Tratado"})
                                updates.append({"column": "Motivo Recusa", "value": f"erro: {lancamento_intervalo_2}"})
                            else:
                                updates.append({"column": "Status", "value": "Não Tratado"})
                                updates.append({"column": "Motivo Recusa", "value": f"erro: {lancamento_intervalo_1}"})
                    else:
                        updates.append({"column": "Status", "value": "Não Tratado"})
                        updates.append({"column": "Motivo Recusa", "value": "Erro no tratamento"})

                else:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": f"erro: {lancamento_2}"})
            else:
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": f"erro: {lancamento_1}"})
        except Exception as e:
            try:
                self.driver.find_element(By.XPATH, "//span[@title='Fechado']//img[@src='/smartgps/images/bt_travar_d.png']")
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "Ponto fechado."})
            except Exception:
                self.driver.find_element(By.XPATH, "//*[text()='Nenhum colaborador corresponde aos filtros de pesquisa selecionados']")
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({"column": "Motivo Recusa", "value": "CPF não encontrado"})

        return updates

