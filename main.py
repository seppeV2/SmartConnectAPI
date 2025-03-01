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
import os
from RequestCard import CallCard, save_json


_username = "9ASmartConnectUSER"
_password = "9APass@word01"
_page = None



app = flet_fastapi.FastAPI()
logger = logging.getLogger('uvicorn.error')

app.mount("/assets", StaticFiles(directory='assets'), name='assets')

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('assets/favicon.ico')


@app.api_route("/import", methods=["GET", "POST", "PUT", "DELETE"])
async def read_root(request: Request):
    
    logger.info("Received request")
    logger.info(f"Method : {request.method}")
    static_url = str(request.url_for('assets', path = 'invoice'))


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
        content[str(_timestamp)] = (method, _timestamp, body, generated_pdf, pdf_name, static_url)
        
        with open('content.json', 'w') as file:
            json.dump(content, file)
        file.close()

        return {"Response": "Succesfully added to file"}

    else:
        
        _card = CallCard(method=request.method, timestamp=_timestamp, body=body,generated_pdf=generated_pdf, pdf_name = pdf_name,static_url=static_url, page=_page)
        _page.list_page.controls.insert( 0,
            _card,
        )
        _page.update()
        _page.content[str(_timestamp)] = (request.method, _timestamp,body, generated_pdf, pdf_name, static_url)
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

   



def create_list_view(page, content):

    if len(content.keys()) > 0:
        keys = list(content.keys())
        keys.sort(reverse=True)
        list_page = ft.ListView(
            expand=True,
            controls = [
                CallCard(method=method, timestamp=timestamp, body=body, generated_pdf = generated_pdf, pdf_name = pdf_name, static_url=static_url, page=page) 
                for (method, timestamp, body, generated_pdf, pdf_name, static_url) in [content[key] for key in keys]
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

