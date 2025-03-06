import flet as ft
import datetime
from pdf2image import convert_from_path
import os
import json
import logging

logger = logging.getLogger('uvicorn.error')


class CallCard(ft.Container):
    
    def __init__(self, method, timestamp, body, generated_pdf, pdf_name,static_url, page, import_id = None):
        self.method = method
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)
        self.timestamp_s = timestamp
        self.generated_pdf = generated_pdf
        self.pdf_name = pdf_name
        self.static_url = static_url
        self.page = page

        self.body = ft.AlertDialog(
            title=ft.Row(
                controls = [
                    ft.Text("Body Content"), 
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=20,
                        icon_color=ft.Colors.WHITE,
                        on_click=lambda e: self.close_body(e)
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),        
            content = self.get_body_content(body),
            open=False,
        )
        

        super().__init__(
            border=ft.border.all(4, ft.Colors.BLACK),
            border_radius=ft.border_radius.all(15),
            alignment=ft.alignment.center,
            height=100,
            margin=ft.margin.all(10),
            content=ft.ListTile(
                trailing = ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_size=40,
                            icon_color=ft.Colors.RED,
                            on_click= lambda e: self.delete_request(e, self, self.parent, self.timestamp_s)
                        ),
                leading= self.create_leading_logo(),
                title=ft.Row(
                    controls = [
                        ft.Text(
                            value= self.timestamp.strftime("%A %d-%m-%Y %H:%M:%S"),
                            size=24
                        ),
                        ft.Text() if import_id == None else ft.Text(value=f'ID : {import_id}', size=24),
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW,
                            icon_size=40,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e: self.open_body(e)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),                
            )
        )     

    def get_body_content(self, body):
        body_content = [
            ft.ListView(
                controls = [
                    ft.Container(
                        content = ft.Text(body, size=20),
                        expand=True,
                    )
                ], 
                width=self.page.width*0.65,
                expand=True,
            ),
        ]

        if self.generated_pdf:
            body_content.insert(
                0,
                ft.TextButton(
                    icon=ft.Icons.DOCUMENT_SCANNER,
                    text='Open embedded PDF',
                    on_click=lambda e: self.open_pdf(e, self.pdf_name),
                    style=ft.ButtonStyle(icon_size=20, text_style=ft.TextStyle(size=20))
                )
            ) 

        return ft.Column(controls=body_content)
    
    def open_pdf(self, e, filename):
        file_path = f'assets/staticFiles/invoice/{filename[0:-4]}/{filename}'
        pdf_document = convert_from_path(file_path)

        pdf_as_pngs = []
        for page_num, img in enumerate(pdf_document):
            path = os.path.join('assets','staticFiles','invoice', f'{filename[0:-4]}')
            page_name = f'{filename[0:-4]}_{page_num+1}.png'
            
            if not os.path.exists(os.path.join(os.path.dirname(__file__),'assets','staticFiles', 'invoice', filename[0:-4], page_name)):
                img.save(os.path.join(path, page_name))
                logger.info(f'PNG Saved: {page_name}')
                
            pdf_as_pngs.append(
                ft.Image(
                    src=os.path.join('staticFiles', 'invoice', filename[0:-4], page_name),
                    fit=ft.ImageFit.FIT_WIDTH,
                    width=0.65*self.page.width
                )
            )
            
        logger.info(f'Following invoices are displayed: {pdf_as_pngs}')
        image_content = ft.Column(
            controls= [img for img in pdf_as_pngs],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True
        )
        
        alert_dialog_pdf = ft.AlertDialog(
            title=ft.Row(
                controls = [
                    ft.Text("Embedded PDF"), 
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        on_click = lambda e: self.close_pdf(e, alert_dialog_pdf)
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=image_content
        )

        self.page.open(alert_dialog_pdf)
        

    def close_pdf(self, e, alert_dialog):
        self.page.close(alert_dialog)
        self.page.update()

    def get_method_color(self, method):
        method_color = {
            "GET": ft.Colors.GREEN,
            "PUT": ft.Colors.BLUE,
            "POST": ft.Colors.YELLOW,
            "DELETE": ft.Colors.RED,
        }
        return method_color[method]

    def open_body(self, e):
        self.page.open(self.body)
        self.page.update()


    def close_body(self, e):
        self.page.close(self.body)
        self.page.update()

    def create_leading_logo(self):
        return ft.Container(
            content=ft.Container(
                content= ft.Text(
                    value= self.method.upper(),
                    text_align=ft.TextAlign.CENTER,
                    style=ft.TextStyle(
                        size=30,
                        weight=ft.FontWeight.BOLD,
                        color=self.get_method_color(self.method),
                    ),
                    
                ), 
            ),
            width = 150,
            border=ft.border.all(3, ft.Colors.BLACK),
            border_radius=ft.border_radius.all(15),
            alignment=ft.alignment.center,

        )
    
    def delete_request(self, e, tile, listView, timestamp):
        listView.controls.remove(tile)
        self.page.content.pop(str(timestamp))
        save_json(self.page.content)
        try:
            os.system(f"rm -r {os.path.join('assets', 'staticFiles','invoice',str(timestamp).replace('.',''))}")
            logger.info('DIRECTORY DELETED')
        except:
            logger.error('DIRECTORY NOT DELETED')
        logger.info(f'Deleted record {timestamp}')
        self.page.update()
 
def save_json(data):
    with open('content.json', 'w') as file:
        json.dump(data, file)