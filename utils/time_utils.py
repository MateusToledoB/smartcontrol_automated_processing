import datetime as dt

class TimeUtils:
    @staticmethod
    def format_elapsed(start_time: dt.datetime, end_time: dt.datetime) -> str:
        elapsed = end_time - start_time
        total_seconds = int(elapsed.total_seconds())
        minutes, seconds = divmod(max(total_seconds, 0), 60)
        return f"{minutes:02d}m {seconds:02d}s"

    @staticmethod
    def verifica_proximidade(horario_hc: dt.time, hora_informada_time: dt.time) -> bool:
        base = dt.date.today()
        hc = dt.datetime.combine(base, horario_hc)
        inf = dt.datetime.combine(base, hora_informada_time)

        # Se a diferença direta passar de 12h, ajusta (significa que cruzou meia-noite)
        if abs((inf - hc).total_seconds()) > 12 * 3600:
            if inf < hc:
                inf += dt.timedelta(days=1)
            else:
                hc += dt.timedelta(days=1)

        return abs((inf - hc).total_seconds()) <= 4 * 3600
    
    @staticmethod
    def retorna_entrada_e_saida_HC(horas):
        entrada = horas[0]
        saida   = horas[-1]

        entrada_str = ":".join(entrada)
        saida_str   = ":".join(saida)

        entrada_horario_contratual_time = dt.datetime.strptime(entrada_str, "%H:%M").time()
        saida_horario_contratual_time   = dt.datetime.strptime(saida_str, "%H:%M").time()

        return entrada_horario_contratual_time, saida_horario_contratual_time
        
    def define_turno_noturno_ou_diurno(entrada_horario_contratual_time: dt.time, saida_horario_contratual_time: dt.time) -> str:
        if entrada_horario_contratual_time.strftime("%H:%M") == "00:00":
            return "Noturno entrada 00"
        elif entrada_horario_contratual_time > saida_horario_contratual_time:
            return "Noturno"
        else:
            return "Diurno"
        

    @staticmethod
    def calcula_diferenca_entrada_saida(data_marcacao_dt, hora_batidada_pelo_colaborador_time, data_registro, entrada_horario_contratual_time, saida_horario_contratual_time, turno):
        # Converter strings em objetos date, se necessário
        if isinstance(data_marcacao_dt, str):
            data_marcacao_dt = dt.datetime.strptime(data_marcacao_dt, "%d/%m/%Y").date()
        if isinstance(data_registro, str):
            data_registro = dt.datetime.strptime(data_registro, "%d/%m/%Y").date()
        
        # Criar objetos datetime combinando data + hora
        hora_batida = dt.datetime.combine(data_marcacao_dt, hora_batidada_pelo_colaborador_time)
        entrada_dt  = dt.datetime.combine(data_registro, entrada_horario_contratual_time)
        saida_dt    = dt.datetime.combine(data_registro, saida_horario_contratual_time)
        
        # Ajustar saída para turnos que passam da meia-noite
        if turno not in ["Noturno entrada 00", "Diurno"]:
            saida_dt += dt.timedelta(days=1)

        # Calcular diferenças em segundos
        dif_entrada = abs((hora_batida - entrada_dt).total_seconds())
        dif_saida   = abs((hora_batida - saida_dt).total_seconds())
        
        # Retornar qual horário está mais próximo
        return "Saida" if dif_entrada < dif_saida else "Entrada"
