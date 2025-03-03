import flet as ft
import datetime
from pdf2image import convert_from_path
import os
import json
import logging

logger = logging.getLogger('uvicorn.error')


class CallCard(ft.Container):
    
    def __init__(self, method, timestamp, body, generated_pdf, pdf_name,static_url, page):
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
            content = ft.ListView(
                    controls = self.get_body_content(page, body), 
                    width=page.width*0.9
                ),
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
                            on_click= lambda e: self.delete_request(e, self, self.parent, page, self.timestamp_s)
                        ),
                leading= self.create_leading_logo(),
                title=ft.Row(
                    controls = [
                        ft.Text(
                            value= self.timestamp.strftime("%A %d-%m-%Y %H:%M:%S"),
                            size=24
                        ),
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW,
                            icon_size=40,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e: self.open_body(e, page)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),                
            )
        )     

    def get_body_content(self, page, body):
        _controls = [
            ft.Container(
                content = ft.Text(body),
                expand=True,
                width=page.width*0.9
            )
        ]

        if self.generated_pdf:
            _controls.insert(
                0,
                ft.TextButton(
                    icon=ft.Icons.DOCUMENT_SCANNER,
                    text='Open embedded PDF',
                    on_click=lambda e: self.open_pdf(e, page, self.pdf_name)
                )
            ) 

        return _controls
    
    def open_pdf(self, e, page, filename):
        file_path = f'assets/invoice/{filename[0:-4]}/{filename}'
        pdf_document = convert_from_path(file_path)

        pdf_as_pngs = []
        for page_num, img in enumerate(pdf_document):
            path = os.path.join('assets','invoice', f'{filename[0:-4]}')
            img.save(os.path.join(path, f'{filename[0:-4]}_{page_num+1}.png'))
            pdf_as_pngs.append(ft.Image(src=f'invoice/{filename[0:-4]}/{filename[0:-4]}_{page_num+1}.png'))
            

        image_content = ft.Row(
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
                        on_click = lambda e: self.close_pdf(e, page, alert_dialog_pdf)
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            content=image_content
        )

        page.open(alert_dialog_pdf)
        

    def close_pdf(self, e, page, alert_dialog):
        page.close(alert_dialog)
        page.update()

    def get_method_color(self, method):
        method_color = {
            "GET": ft.Colors.GREEN,
            "PUT": ft.Colors.BLUE,
            "POST": ft.Colors.YELLOW,
            "DELETE": ft.Colors.RED,
        }
        return method_color[method]

    def open_body(self, e, page):
        page.open(self.body)
        page.update()


    def close_body(self, e, page):
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
    
    def delete_request(self, e, tile, listView, page, timestamp):
        listView.controls.remove(tile)
        self.page.content.pop(str(timestamp))
        save_json(self.page.content)
        try:
            os.system(f'rm -r {os.path.join('assets','invoice',str(timestamp).replace('.',''))}')
            logger.info('DIRECTORY DELETED')
        except:
            logger.error('DIRECTORY NOT DELETED')
        logger.info(f'Deleted record {timestamp}')
        page.update()
 
def save_json(data):
    with open('content.json', 'w') as file:
        json.dump(data, file)