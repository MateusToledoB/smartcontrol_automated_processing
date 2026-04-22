import smartsheet

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
            row = smartsheet.models.Row()
            row.id = item["row_id"]

            cells = []
            for u in item["updates"]:
                cell = smartsheet.models.Cell()
                cell.column_id = column_map[u["column"]]
                cell.value = u["value"]
                cells.append(cell)

            row.cells = cells
            rows_to_update.append(row)

        # Envia em lote
        response = smart.Sheets.update_rows(sheet_id, rows_to_update)

        while response.message != 'SUCCESS':
            response = smart.Sheets.update_rows(sheet_id, rows_to_update)

    @staticmethod
    def return_df_crs():
        sheet_id = settings.SHEET_ID_EXCECOES_VALIDAS

        


                