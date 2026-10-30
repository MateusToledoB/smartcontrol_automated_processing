from services.treatment_rules import TreatmentRules


class FaltaBancoHorasDescontar041:
    """
    Tratamento exclusivo para:

        Motivo Alteração = 04.1 - Faltas sem justificativa
        Classificação da Falta = Banco de Horas - Descontar

    Regras:
        1. Antes de qualquer tratamento, a folha da data precisa estar aberta.
        2. Antes de abrir o BH, não pode haver quantidade ímpar de marcações válidas.
        3. Dentro do BH, a soma dos saldos da linha não pode ser menor que -20:00.
        4. Passando nas validações, reaproveita TreatmentRules.change_rule_bh para
           desmarcar a regra automática, classificar a ausência como BH e salvar.
    """

    def __init__(self, driver, row_id, sheet_id, token, data_registro):
        self.driver = driver
        self.row_id = row_id
        self.sheet_id = sheet_id
        self.token = token
        self.data_registro = data_registro

    def adjust(self):
        updates = []

        try:
            # ---------------------------------------------------------
            # REGRA 0 - PONTO PRECISA ESTAR ABERTO
            # ---------------------------------------------------------
            ponto_aberto, status_folha = (
                TreatmentRules.verificar_ponto_aberto_antes_bh(
                    self.driver,
                    self.data_registro,
                )
            )

            if not ponto_aberto:
                print(
                    f"[04.1 BH] Não tratado: ponto fechado/indisponível "
                    f"em {self.data_registro} - status: {status_folha!r}"
                )
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({
                    "column": "Motivo Recusa",
                    "value": "ponto fechado"
                })
                return updates

            # ---------------------------------------------------------
            # REGRA 1 - BATIDAS ÍMPARES
            # ---------------------------------------------------------
            tem_batida_impar, total_batidas, horarios = (
                TreatmentRules.verificar_batidas_impares_antes_bh(
                    self.driver,
                    self.data_registro,
                )
            )

            if tem_batida_impar:
                print(
                    f"[04.1 BH] Não tratado: {total_batidas} batida(s) "
                    f"válida(s) no dia {self.data_registro}: {horarios}"
                )
                updates.append({"column": "Status", "value": "Não Tratado"})
                updates.append({
                    "column": "Motivo Recusa",
                    "value": "contem batidas impar"
                })
                return updates

            # ---------------------------------------------------------
            # REGRA 2 - SALDO TOTAL NÃO PODE FICAR ABAIXO DE -20:00
            # + CLASSIFICAÇÃO NO BANCO DE HORAS
            # ---------------------------------------------------------
            response_change_rule_bh = TreatmentRules.change_rule_bh(
                self.driver,
                self.data_registro,
                updates,
                validar_limite_negativo=True,
            )

            if response_change_rule_bh:
                return response_change_rule_bh

            updates.append({"column": "Status", "value": "Tratado"})
            return updates

        except Exception as e:
            print(f"[04.1 BH] Erro inesperado: {e}")
            updates.append({"column": "Status", "value": "Não Tratado"})
            updates.append({
                "column": "Motivo Recusa",
                "value": "Não foi possivel tratar Banco de Horas - Descontar"
            })
            return updates
