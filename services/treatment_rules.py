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
    def verificar_ponto_aberto_antes_bh(driver, data_registro):
        """
        Verifica o status da folha na linha da data, antes de qualquer
        tentativa de tratamento de banco de horas.

        A coluna 5 da tabela principal corresponde a "Status folha".
        O tratamento somente pode continuar quando o status encontrado
        for "Aberto".

        Retorna:
            tuple[bool, str]:
                (ponto_aberto, status_encontrado)
        """
        driver.switch_to.default_content()

        linha_xpath = (
            "//table[@id='scroll_table_1']"
            "//tbody/tr["
            f"td[6][normalize-space()='{data_registro}']"
            "]"
        )

        linha_dia = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, linha_xpath))
        )

        status_td = linha_dia.find_element(By.XPATH, "./td[5]")

        # O SmartGPS normalmente informa o estado no atributo title
        # do span/img do cadeado, por exemplo: title="Aberto".
        elementos_status = status_td.find_elements(By.XPATH, ".//*[@title]")
        titulos = []

        for elemento in elementos_status:
            titulo = (elemento.get_attribute("title") or "").strip()
            if titulo and titulo not in titulos:
                titulos.append(titulo)

        status_encontrado = titulos[0] if titulos else status_td.text.strip()
        ponto_aberto = status_encontrado.lower() == "aberto"

        print(
            f"[04.1 BH] Data {data_registro} - "
            f"status folha: {status_encontrado!r}"
        )

        if ponto_aberto:
            print(f"[04.1 BH] Data {data_registro} - ponto ABERTO.")
        else:
            print(
                f"[04.1 BH] Data {data_registro} - "
                "ponto FECHADO / indisponivel para tratamento."
            )

        return ponto_aberto, status_encontrado

    @staticmethod
    def verificar_batidas_impares_antes_bh(driver, data_registro):
        """
        Verifica as marcações válidas do dia diretamente na tela principal
        da folha ponto, antes de abrir o tratamento de banco de horas.

        A contagem considera somente a coluna "Marcações" (td[8]) e ignora
        a coluna "Marcações desconsideradas" (td[9]).

        Retorna:
            tuple[bool, int, list[str]]:
                (tem_batida_impar, total_batidas, horarios_encontrados)
        """
        driver.switch_to.default_content()

        linha_xpath = (
            "//table[@id='scroll_table_1']"
            "//tbody/tr["
            f"td[6][normalize-space()='{data_registro}']"
            "]"
        )

        linha_dia = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, linha_xpath))
        )

        marcacoes = linha_dia.find_elements(By.XPATH, "./td[8]//span")
        horarios = [marcacao.text.strip() for marcacao in marcacoes if marcacao.text.strip()]
        total_batidas = len(marcacoes)

        print(
            f"[04.1 BH] Data {data_registro} - "
            f"batidas válidas: {total_batidas} - horários: {horarios}"
        )

        return total_batidas % 2 != 0, total_batidas, horarios

    @staticmethod
    def _minutos_para_hhmm(total_minutos, mostrar_sinal=False):
        if total_minutos < 0:
            sinal = "-"
        elif total_minutos > 0 and mostrar_sinal:
            sinal = "+"
        else:
            sinal = ""

        total_abs = abs(total_minutos)
        horas, minutos = divmod(total_abs, 60)
        return f"{sinal}{horas:02d}:{minutos:02d}"

    @staticmethod
    def _saldo_total_linha_bh(linha_dia):
        """
        Soma os saldos de BH exibidos nos cards da linha da data,
        respeitando o sinal de cada valor.

        Exemplos:
            12:24 + 05:42 = +18:06
            -15:00 + 05:42 = -09:18
            -15:00 + -06:00 = -21:00

        Valores sem sinal sao considerados positivos.
        """
        saldos_encontrados = []
        total_saldo = 0

        # O saldo mostrado na tela de tratamento do BH usa cards como:
        # <div class="v-card ... d-flex align-center justify-center ...">-21:28</div>
        # ou valores positivos sem o sinal, como 12:24.
        # Ao buscar apenas esses cards, evita-se somar outros HH:MM da linha.
        elementos = linha_dia.find_elements(
            By.XPATH,
            ".//div[contains(@class,'v-card') "
            "and contains(@class,'align-center') "
            "and contains(@class,'justify-center')]"
        )

        for elemento in elementos:
            texto = elemento.text.strip()
            if not texto:
                continue

            match = re.fullmatch(r"([+-]?)(\d+):([0-5]\d)", texto)
            if not match:
                continue

            sinal = match.group(1)
            horas = int(match.group(2))
            minutos = int(match.group(3))
            saldo_minutos = horas * 60 + minutos

            if sinal == "-":
                saldo_minutos *= -1

            saldos_encontrados.append(texto)
            total_saldo += saldo_minutos

        print(
            f"[04.1 BH] Saldos da linha: {saldos_encontrados} - "
            f"total: {TreatmentRules._minutos_para_hhmm(total_saldo, mostrar_sinal=True)}"
        )

        return total_saldo

    @staticmethod
    def change_rule_bh(driver, data_registro, updates, validar_limite_negativo=False):
        try:
            banco_horas = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Tratar banco de horas']"))
            )

            driver.execute_script("arguments[0].click();", banco_horas)

            SeleniumUtils.iframe_acess(driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

            linha_xpath = (
                f"//td[contains(normalize-space(), '{data_registro}')]"
                f"/parent::tr"
            )

            linha_dia = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, linha_xpath))
            )

            # Regra exclusiva do 04.1 - Banco de Horas - Descontar:
            # soma todos os saldos da linha, respeitando positivos e negativos.
            # Se o saldo total ficar abaixo de -20:00, nao trata.
            if validar_limite_negativo:
                total_saldo = TreatmentRules._saldo_total_linha_bh(linha_dia)
                limite_negativo = -(20 * 60)

                if total_saldo < limite_negativo:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({
                        "column": "Motivo Recusa",
                        "value": "a mais de 20 horas negativas"
                    })
                    driver.switch_to.default_content()
                    return updates

            checkbox_xpath = ".//input[@type='checkbox']"

            if validar_limite_negativo:
                # Para o 04.1, seleciona explicitamente o rádio de Banco de Horas.
                radio_xpath = (
                    ".//input[@type='radio' and @value='2' "
                    "and contains(@id,'ausencia_tipo_bh_')]"
                )
                desc_element = WebDriverWait(driver, 20).until(
                    lambda d: linha_dia.find_element(By.XPATH, radio_xpath)
                )
            else:
                # Preserva o comportamento atual das demais regras que já usam
                # change_rule_bh, especialmente o fluxo 09.1.
                radios = WebDriverWait(driver, 20).until(
                    lambda d: linha_dia.find_elements(By.XPATH, ".//input[@type='radio']")
                )
                desc_element = radios[0]

            # Se o rádio estiver bloqueado pela regra automática, desmarca o checkbox.
            if not desc_element.is_enabled():
                checkboxes = WebDriverWait(driver, 20).until(
                    lambda d: linha_dia.find_elements(By.XPATH, checkbox_xpath)
                )

                if not checkboxes:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({
                        "column": "Motivo Recusa",
                        "value": "Não foi possivel alterar a regra"
                    })
                    driver.switch_to.default_content()
                    return updates

                driver.execute_script("arguments[0].click();", checkboxes[0])

                WebDriverWait(driver, 10).until(
                    lambda d: desc_element.is_enabled()
                )

            # Classifica a ausência como Banco de Horas.
            driver.execute_script("arguments[0].click();", desc_element)

            # Para o 04.1, usa espera real dos elementos/retorno do sistema.
            # Para os demais fluxos que reutilizam change_rule_bh, preserva
            # exatamente o comportamento antigo.
            if validar_limite_negativo:
                botao_salvar = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Salvar']"))
                )

                driver.execute_script("arguments[0].click();", botao_salvar)

                print("[04.1 BH] Salvar acionado. Aguardando retorno do sistema...")

                # Não considera apenas a presença do span: aguarda existir uma
                # notificação visível e com texto preenchido.
                notify_mudanca_regra = WebDriverWait(driver, 30).until(
                    lambda d: next(
                        (
                            elemento
                            for elemento in d.find_elements(
                                By.XPATH,
                                "//span[@style='font-size: 11px;']"
                            )
                            if elemento.is_displayed() and elemento.text.strip()
                        ),
                        False
                    )
                )

                texto_notify = notify_mudanca_regra.text.strip()

                print(
                    f"[04.1 BH] Retorno ao salvar: {texto_notify}"
                )

                if texto_notify == "Tratamento de banco de horas salvo com sucesso":
                    print("[04.1 BH] Tratamento salvo com sucesso.")

                    # Sai do iframe do Banco de Horas para localizar o fechar
                    # do diálogo principal.
                    driver.switch_to.default_content()

                    botao_fechar = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@title='Fechar']"))
                    )

                    driver.execute_script("arguments[0].click();", botao_fechar)

                    # Aguarda a janela/modal realmente desaparecer antes de
                    # liberar o fluxo para a próxima linha.
                    WebDriverWait(driver, 20).until(
                        EC.staleness_of(botao_fechar)
                    )

                    print("[04.1 BH] Janela de Banco de Horas fechada.")
                else:
                    updates.append({"column": "Status", "value": "Não Tratado"})
                    updates.append({"column": "Motivo Recusa", "value": texto_notify})
                    driver.switch_to.default_content()
                    return updates

            else:
                # Fluxo antigo preservado para 09.1 e demais regras.
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
                        driver.switch_to.default_content()
                        return updates
        except Exception as e:
            print(f"[change_rule_bh] Erro: {e}")
            driver.switch_to.default_content()
            updates.append({"column": "Status", "value": "Não Tratado"})
            updates.append({"column": "Motivo Recusa", "value": "Não foi possivel alterar a regra"})
            return updates

    @staticmethod
    def change_rule_bh_temp(driver, data_registro, updates):
        try:
            banco_horas = WebDriverWait(driver, 8).until(
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
        
    @staticmethod
    def records_observation(driver, observacao, data_registro, updates):
        driver.switch_to.default_content()
        elemento = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@title="Fechar"]'))
        )
        driver.execute_script("arguments[0].click();", elemento)
        
        # espera o modal SUMIR de verdade
        WebDriverWait(driver, 10).until(
            EC.staleness_of(elemento)
        )
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='hora_extra_button']"))
        ).click()
        
        SeleniumUtils.iframe_acess(driver, "/html/body/div[3]/div/div[1]/div/div/div[2]/div/iframe")

        input_observacao = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((
                    By.XPATH,f"//td[normalize-space()='{data_registro}']/preceding-sibling::td//input[contains(@name,'observacao')]"
                ))
            )
        input_observacao.clear()
        input_observacao.send_keys(observacao)
        input_observacao.click()
        time.sleep(3)
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[@value='Salvar']"))
        ).click()
        time.sleep(2)
        notify = WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.XPATH,'//*[@id="top_pad_div"]/div/div/div[1]/span')))
        notify = notify.get_attribute("innerText")
        #print(f'Notificação hora extra: {notify}')
        if notify != "Registros salvos com sucesso":
            updates.append({"column": "Motivo Recusa", "value": "Erro ao lançar observacao falta > 3h"})
