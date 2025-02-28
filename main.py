import flet.fastapi as flet_fastapi
from fastapi import Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import flet as ft
import json
import base64
import datetime
import uvicorn
import logging
from bs4 import BeautifulSoup 
from pdf2image import convert_from_path
import os
import httpx 


_username = "9ASmartConnectUSER"
_password = "9APass@word01"
_page = None



app = flet_fastapi.FastAPI()
logger = logging.getLogger('uvicorn.error')

app.mount("/assets", StaticFiles(directory='assets'), name='assets')

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('assets/favicon.ico')

@app.get('/get_static_urls', include_in_schema=False)
async def get_staic_url(request: Request):
    global static_url
    static_url = request.url_for('assets', path = 'invoice')
    return {'response' : 'OK'}


@app.api_route("/import", methods=["GET", "POST", "PUT", "DELETE"])
async def read_root(request: Request):
    global static_url
    
    logger.info("Received request")
    logger.info(f"Method : {request.method}")

    try:
        _basicAuth = str(request.headers['authorization']).split(' ')[-1]
        decoded_auth = base64.b64decode(_basicAuth).decode('utf8')
        (decoded_auth_usr, decoded_auth_passwd) = (decoded_auth.split(':')[0], decoded_auth.split(':')[1])
    except KeyError:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    
    if not check_auth(decoded_auth_usr, decoded_auth_passwd):
        raise HTTPException(status_code=401, detail="Unauthorized access")
    
    
    _timestamp = datetime.datetime.now().timestamp()
    method = request.method
    body_raw = await request.body()
    
    try:
        body = json.loads(body_raw.decode('utf-8')) 
    except: 
        body = body_raw.decode('utf-8')

    generated_pdf, pdf_name = ubl_transform(body, _timestamp)
        
    if _page is None: 
        
        with open('content.json', 'r') as file: 
            content = json.load(file)
        file.close()
        content[str(_timestamp)] = (method, _timestamp, body, generated_pdf, pdf_name)
        
        with open('content.json', 'w') as file:
            json.dump(content, file)
        file.close()

        return {"Response": "Succesfully added to file"}

    else:
        
        _card = CallCard(method=request.method, timestamp=_timestamp, body=body,generated_pdf=generated_pdf, pdf_name = pdf_name, page=_page)
        _page.list_page.controls.insert( 0,
            _card,
        )
        _page.update()
        _page.content[str(_timestamp)] = (request.method, _timestamp,body, generated_pdf, pdf_name)
        save_json(_page.content)
        return {"Response": "Succesfully received + updated app"}

def check_auth(username, password):
    return (_username == username) and (_password == password)


def ubl_transform(body, time):
    try:
        pdf = BeautifulSoup(body, "xml").find("cbc:EmbeddedDocumentBinaryObject").contents[0]
        file_name = f'{str(time).replace('.','')}.pdf'
        if pdf != None:
            path = os.path.join('assets','invoice',f'{file_name[0:-4]}')
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path,file_name), "wb") as f:
                f.write(base64.b64decode(pdf))

            return True, file_name
        else:
            return False, None
    except:
        return False, None

    
def delete_request(e, tile, listView, page, timestamp):
    global _page
    listView.controls.remove(tile)
    _page.content.pop(str(timestamp))
    save_json(_page.content)
    try:
        os.system(f'rm -r {os.path.join('assets','invoice',str(timestamp).replace('.',''))}')
        logger.info('DIRECTORY DELETED')
    except:
        logger.error('DIRECTORY NOT DELETED')
    logger.info(f'Deleted record {timestamp}')
    page.update()

class CallCard(ft.Container):
    
    def __init__(self, method, timestamp, body, generated_pdf, pdf_name, page):
        self.method = method
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)
        self.timestamp_s = timestamp
        self.generated_pdf = generated_pdf
        self.pdf_name = pdf_name

        self.body = ft.AlertDialog(
            title=ft.Row(
                controls = [
                    ft.Text("Body Content"), 
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=20,
                        icon_color=ft.Colors.WHITE,
                        on_click=lambda e: self.close_body(e, page)
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
                            on_click= lambda e: delete_request(e, self, self.parent, page, self.timestamp_s)
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
        global _page, static_url
        file_path = f'assets/invoice/{filename[0:-4]}/{filename}'
        pdf_document = convert_from_path(file_path)

        pdf_as_pngs = []
        for page_num, img in enumerate(pdf_document):
            path = os.path.join('assets','invoice', f'{filename[0:-4]}')
            img.save(os.path.join(path, f'{filename[0:-4]}_{page_num+1}.png'))
            pdf_as_pngs.append(ft.Image(src=f'{static_url}/{filename[0:-4]}/{filename[0:-4]}_{page_num+1}.png'))
            

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
        page.close(self.body)
        page.update()

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
    
def save_json(data):
    with open('content.json', 'w') as file:
        json.dump(data, file)


def create_list_view(page, content):

    if len(content.keys()) > 0:
        keys = list(content.keys())
        keys.sort(reverse=True)
        list_page = ft.ListView(
            expand=True,
            controls = [
                CallCard(method=method, timestamp=timestamp, body=body, generated_pdf = generated_pdf, pdf_name = pdf_name, page=page) 
                for (method, timestamp, body, generated_pdf, pdf_name) in [content[key] for key in keys]
            ],
        )

    else:
        list_page = ft.ListView(
            expand=True
        )
    
    return list_page
    
    

async def main(page: ft.Page):
    global _page
    _page = page

    logger.info("OPEN NEW PAGE")

    with open('content.json', 'r') as file: 
        _page.content = json.load(file)

    _page.list_page = create_list_view(page, page.content)

    _appbar = ft.AppBar(
        leading = ft.Text(),
        title= ft.SafeArea(
            content= ft.Text(
                value='Smart Connect API', 
                text_align=ft.TextAlign.CENTER,
                size=40,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,            
            ),
        ),
        center_title = True,
    )

    _page.views[-1].appbar = _appbar
    _page.views[-1].controls.append(
        ft.Divider(thickness=3, color=ft.Colors.WHITE)
    )
    _page.views[-1].controls.append(
        _page.list_page
    )

    _page.update()

app.mount("/", flet_fastapi.app(main, assets_dir='assets'))


if __name__ == "__main__":
    uvicorn.run('main:app', host='0.0.0.0')

