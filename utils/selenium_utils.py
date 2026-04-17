import datetime as dt
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.settings import settings

class SeleniumUtils():
    @staticmethod
    def retorna_entrada_e_saida_HC(horas):
        entrada = horas[0]
        saida   = horas[-1]

        entrada_str = ":".join(entrada)
        saida_str   = ":".join(saida)

        entrada_horario_contratual_time = dt.datetime.strptime(entrada_str, "%H:%M").time()
        saida_horario_contratual_time   = dt.datetime.strptime(saida_str, "%H:%M").time()

        return entrada_horario_contratual_time, saida_horario_contratual_time
    
    @staticmethod
    def saida_maior_que_hc_em_2h(saida_hc: dt.time, saida_informada_str: str) -> bool:
        # cria uma data fictícia (qualquer uma serve)
        base_date = dt.date.today()

        # transforma em datetime
        saida_hc_dt = dt.datetime.combine(base_date, saida_hc)
        saida_informada_dt = dt.datetime.strptime(saida_informada_str, "%H:%M").replace(
            year=base_date.year,
            month=base_date.month,
            day=base_date.day
        )

        # soma 2 horas na saída HC
        saida_hc_mais_2h = saida_hc_dt + dt.timedelta(hours=2)

        return saida_informada_dt >= saida_hc_mais_2h
    
    @staticmethod
    def lancar_horario_no_sistema(data_escrever, horario_escrever, driver) -> str:
        data_marcacao = driver.find_element(By.XPATH, '//*[@id="data_marcacao"]')
        driver.execute_script("arguments[0].value = arguments[1];", data_marcacao, data_escrever)
        time.sleep(1)
        campo_hora_marcacao = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='hora_marcacao']"))
        )
        campo_hora_marcacao.clear()
        campo_hora_marcacao.send_keys(horario_escrever)
        time.sleep(1)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='motivo_marcacao']"))
        ).click()
  
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[text()='Ajustes']"))
        ).click()
       
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "(//*[@title='Salvar'])[3]"))
        ).click()
        time.sleep(2)
        WebDriverWait(driver, 200).until(
            EC.invisibility_of_element_located((By.XPATH, "//*[@data-text='Aguarde...']"))
        )
        time.sleep(2)
        notify = WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.XPATH,'//*[@id="top_pad_div"]/div/div/div[1]/span')))
        notify = notify.get_attribute("innerText")
        # print(f"Notificação após salvar marcação: {notify}")
        return notify
    
    @staticmethod
    def extrair_intervalo(horario_str: str) -> tuple[str, str]:
        # captura todos os horários HH:MM
        horarios = re.findall(r"\d{2}:\d{2}", horario_str)

        if len(horarios) < 4:
            raise ValueError("Formato de horário inválido")

        fim_primeiro_turno = dt.datetime.strptime(horarios[1], "%H:%M")
        inicio_segundo_turno = dt.datetime.strptime(horarios[2], "%H:%M")

        return (
            fim_primeiro_turno.strftime("%H:%M"),
            inicio_segundo_turno.strftime("%H:%M"),
        )
    
    @staticmethod
    def calcular_tempo_intervalo(inicio: str, fim: str) -> dt.timedelta:
        """
        Calcula a duração do intervalo a partir de strings "HH:MM",
        tratando virada de dia
        """
        base_date = dt.date.today()

        inicio_time = dt.datetime.strptime(inicio, "%H:%M").time()
        fim_time = dt.datetime.strptime(fim, "%H:%M").time()

        inicio_dt = dt.datetime.combine(base_date, inicio_time)
        fim_dt = dt.datetime.combine(base_date, fim_time)

        # virou o dia
        if fim_dt <= inicio_dt:
            fim_dt += dt.timedelta(days=1)

        return fim_dt - inicio_dt
    
    @staticmethod
    def define_turno_noturno_ou_diurno(entrada_horario_contratual_time: dt.time, saida_horario_contratual_time: dt.time) -> str:
        if entrada_horario_contratual_time.strftime("%H:%M") == "00:00":
            return "Noturno entrada 00"
        elif entrada_horario_contratual_time > saida_horario_contratual_time:
            return "Noturno"
        else:
            return "Diurno"
        
    @staticmethod
    def gerar_intervalo(
        data_registro: str,
        entrada: str,
        saida: str,
        intervalo: dt.timedelta,
        formato_data: str = "%d/%m/%Y",
        formato_hora: str = "%H:%M",
    ) -> tuple[str, str, str, str]:
        data_base = dt.datetime.strptime(data_registro, formato_data).date()

        entrada_dt = dt.datetime.combine(
            data_base, dt.datetime.strptime(entrada, formato_hora).time()
        )
        saida_dt = dt.datetime.combine(
            data_base, dt.datetime.strptime(saida, formato_hora).time()
        )

        if saida_dt <= entrada_dt:
            saida_dt += dt.timedelta(days=1)

        inicio_intervalo_dt = saida_dt - dt.timedelta(hours=4)
        fim_intervalo_dt = inicio_intervalo_dt + intervalo

        return (
            inicio_intervalo_dt.strftime(formato_data),
            inicio_intervalo_dt.strftime(formato_hora),
            fim_intervalo_dt.strftime(formato_data),
            fim_intervalo_dt.strftime(formato_hora),
        )
    
    @staticmethod
    def ajustar_data_intervalo(
            data_registro: str,
            entrada_intervalo: str,
            saida_intervalo: str,
            formato_data: str = "%d/%m/%Y",
            formato_hora: str = "%H:%M"
        ) -> tuple[str, str]:
            """
            Verifica se o intervalo atravessa a noite e ajusta as datas
            Retorna:
                (data_entrada_intervalo, data_saida_intervalo)
            """

            data_base = dt.datetime.strptime(data_registro, formato_data).date()

            hora_entrada = dt.datetime.strptime(entrada_intervalo, formato_hora).time()
            hora_saida = dt.datetime.strptime(saida_intervalo, formato_hora).time()

            data_entrada_intervalo = data_base

            # Se a saída for "menor" que a entrada, virou o dia
            if hora_saida < hora_entrada:
                data_saida_intervalo = data_base + dt.timedelta(days=1)
            else:
                data_saida_intervalo = data_base

            return (
                data_entrada_intervalo.strftime(formato_data),
                data_saida_intervalo.strftime(formato_data)
            )

    @staticmethod
    def iframe_acess(driver, xpath_iframe):
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, xpath_iframe))
        )
        driver.switch_to.frame(iframe)

    @staticmethod
    def login_motus(driver, user, password):
        driver.get(settings.URL_MOTUS)

        user_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='input-9']"))
        )

        password_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='input-12']"))
        )

        user_element.send_keys(user)
        password_element.send_keys(password)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='Entrar']"))
        ).click()

    def search_cpf(driver, cpf, data_registro):
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='Ponto']"))
        ).click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='Tratar']"))
        ).click()
    
        campo_data_inicial = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='data_inicial']"))
        )

        campo_data_final = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='data_final']"))
        )

        driver.execute_script("arguments[0].value = arguments[1];", campo_data_inicial, data_registro)
        driver.execute_script("arguments[0].value = arguments[1];", campo_data_final, data_registro)
       
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='_colaborador_tipo_filtro_Funcionario.Cpf']"))
        ).click()

        cpf_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='_colaborador_filtro']"))
        )

        cpf_input.send_keys(cpf)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@value='Pesquisar']"))
        ).click()
      
    @staticmethod
    def verifica_lancamento(driver):
        motivos = [
            "Atestado Médico",
            "Abandono",
            "Falta",
            "Dia Justificado Empresa",
            "Atestado Odontológico",
            "Serviço Sindical",
            "Afastado",
            "Licença Paternidade",
            "Licença Casamento",
            "Treinamento / Reciclagem",
            "Demissão",
            "Integração Cliente",
            "Hora Justificada Empresa",
            "Licença Óbito",
            "Acompanhamento de Menores"
        ]

        for motivo in motivos:
            elementos = driver.find_elements(
                By.XPATH,
                f"//td[normalize-space(text())='{motivo}']"
            )

            if elementos:
                return motivo

        return None

    @staticmethod
    def verifica_lancamento_Temp(driver):
        motivos = [
            "Atestado Médico",
            "Abandono",
            "Falta",
            "REP - Dia Justificado",
            "Atestado Odontológico",
            "Serviço Sindical",
            "Afastado",
            "Licença Paternidade",
            "Licença Casamento",
            "Treinamento / Reciclagem",
            "Demissão",
            "Integração",
            "REP - Hora Justificado",
            "Licença Óbito",
            "Acompanhamento de Menores"
        ]

        for motivo in motivos:
            elementos = driver.find_elements(
                By.XPATH,
                f"//td[normalize-space(text())='{motivo}']"
            )

            if elementos:
                return motivo

        return None