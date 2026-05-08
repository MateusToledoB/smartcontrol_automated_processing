import smartsheet
import pandas as pd
from core.settings import settings

class SmartsheetClient:
    SMARTSHEET_TOKEN = settings.SMARTSHEET_TOKEN
    
    @staticmethod
    def setup_smartsheet(sheet_id):
        #comc chamar setup_smartsheet
        #EX: sheet, rows, token, sheet_id, smart = setup_smartsheet('id_aqui')
        
        # Token de acesso da API Smartsheet
        token = SmartsheetClient.SMARTSHEET_TOKEN
        # Conecta à API
        smart = smartsheet.Smartsheet(token)
        # Id da planilha Smartsheet
        sheet_id = sheet_id
        # Assume valores da Planilha 
        sheet = smart.Sheets.get_sheet(sheet_id)
        rows = sheet.rows
        return sheet, rows, token, sheet_id, smart
    
    @staticmethod
    def update_smartsheet(column_title, cell_value, row_id, sheet_id, token):
        # Declara max_rows como global para acessá-lo dentro da função
            
            smart = smartsheet.Smartsheet(token)
            sheet = smart.Sheets.get_sheet(sheet_id)
            # Encontra o ID da coluna com o título fornecido
            column_id = [col.id for col in sheet.columns if col.title == column_title][0]
            
            # Cria uma célula na coluna com o título fornecido e o valor fornecido
            cell = smartsheet.models.Cell()
            cell.column_id = column_id
            cell.value = cell_value
            
            # Cria uma linha e adiciona a célula a ela
            updated_row = smartsheet.models.Row()
            updated_row.id = row_id
            updated_row.cells.append(cell)
            
            # Atualiza a linha na planilha
            response = smart.Sheets.update_rows(sheet_id, [updated_row])
            
            # Verifica se a atualização foi bem-sucedida
            while response.message != 'SUCCESS':
                response = smart.Sheets.update_rows(sheet_id, [updated_row])

    @staticmethod
    def add_update(updates: list, column_title: str, cell_value):
        updates.append({
            "column": column_title,
            "value": cell_value
        })

    @staticmethod
    def update_bulk(all_updates, sheet_id):
        smart = smartsheet.Smartsheet(SmartsheetClient.SMARTSHEET_TOKEN)
        sheet = smart.Sheets.get_sheet(sheet_id)

        # Mapeia nome da coluna -> column_id
        column_map = {col.title: col.id for col in sheet.columns}

        rows_to_update = []

        for item in all_updates:
            if "row_id" not in item:
                print("[update_bulk] Item ignorado: row_id ausente.")
                continue

            updates = item.get("updates", [])
            if not updates:
                continue

            # Blindagem: garante apenas 1 valor por coluna na mesma linha.
            # Se houver duplicidade, mantemos o ultimo valor recebido.
            dedup_updates = {}
            for update in updates:
                column_name = update.get("column")
                if column_name is None:
                    print(f"[update_bulk] Linha {item['row_id']}: update ignorado por coluna ausente.")
                    continue
                if column_name not in column_map:
                    print(f"[update_bulk] Linha {item['row_id']}: coluna '{column_name}' nao existe na planilha. Update ignorado.")
                    continue
                dedup_updates[column_name] = update.get("value")

            if not dedup_updates:
                continue

            row = smartsheet.models.Row()
            row.id = item["row_id"]

            cells = []
            for column_name, value in dedup_updates.items():
                cell = smartsheet.models.Cell()
                cell.column_id = column_map[column_name]
                cell.value = value
                cells.append(cell)

            row.cells = cells
            rows_to_update.append(row)

        if not rows_to_update:
            print("[update_bulk] Nenhuma linha valida para atualizar em lote.")
            return

        # Envia em lote
        response = smart.Sheets.update_rows(sheet_id, rows_to_update)

        if response.message != 'SUCCESS':
            response = smart.Sheets.update_rows(sheet_id, rows_to_update)
            if response.message != 'SUCCESS':
                print("Erro ao atualizar em lote:", response.message)

    @staticmethod
    def return_df_crs():
        sheet_id = settings.SHEET_ID_EXCECOES_VALIDAS

        # Inicializa cliente
        smartsheet_client = smartsheet.Smartsheet(settings.SMARTSHEET_TOKEN)

        # Puxa a planilha
        sheet = smartsheet_client.Sheets.get_sheet(sheet_id)

        # Mapeia columnId -> nome da coluna
        columns_map = {col.id: col.title for col in sheet.columns}

        data = []

        # Itera pelas linhas
        for row in sheet.rows:
            row_data = {}

            for cell in row.cells:
                col_name = columns_map.get(cell.column_id)
                value = cell.value if cell.value is not None else cell.display_value
                row_data[col_name] = value

            data.append(row_data)

        # Cria DataFrame
        df = pd.DataFrame(data)

        return df

    def return_validation_cr(df: pd.DataFrame, valor_referencia: str, tipo: str):
        """
        df: DataFrame
        valor_referencia: valor que será buscado na coluna 'CR'
        tipo: 'hora' ou 'dia'
        """

        # Filtra a linha pelo CR
        linha = df[df['CR'].astype(str).str.contains(valor_referencia, na=False)]

        if linha.empty:
            return 'NÃO'

        linha = linha.iloc[0]  # pega a primeira ocorrência

        if tipo.lower() == "hora":
            return linha.get("Hora Justificada Empresa")
        elif tipo.lower() == "dia":
            return linha.get("Dia Justificado Empresa")
        else:
            raise ValueError("Tipo deve ser 'hora' ou 'dia'")




                
