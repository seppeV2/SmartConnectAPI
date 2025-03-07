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
from azure.storage.blob import BlobClient


_username = "9ASmartConnectUSER"
_password = "9APass@word01"
_page = None

app = flet_fastapi.FastAPI()
logger = logging.getLogger('uvicorn.error')

try:
    _SAS_blob_url = os.environ.get('SAS_CONNECTION_STRING_SMARTCONNECT')
    test_value = os.environ.get('SAS_TEST_VALUE')
    if _SAS_blob_url != None:
        logger.info("SAS Connection string found")
        logger.info(f"Test value = {test_value}")
    else:
        logger.info("SAS Connection string not found")
        _SAS_blob_url = "https://st9asmartconnectapi.blob.core.windows.net/ct9asmartconnectapi/9Asmartconnect_api_content.json?sp=rw&st=2025-03-07T10:56:24Z&se=2026-03-07T18:56:24Z&spr=https&sv=2022-11-02&sr=b&sig=5eJBdLVHIpPnupYVcSQkzJQgQ%2BOT0kDE5GlDRYQEZVo%3D"


except:
    logger.info("error in reading Connection string")
    _SAS_blob_url = "https://st9asmartconnectapi.blob.core.windows.net/ct9asmartconnectapi/9Asmartconnect_api_content.json?sp=rw&st=2025-03-07T10:56:24Z&se=2026-03-07T18:56:24Z&spr=https&sv=2022-11-02&sr=b&sig=5eJBdLVHIpPnupYVcSQkzJQgQ%2BOT0kDE5GlDRYQEZVo%3D"

_blob_client = BlobClient.from_blob_url(_SAS_blob_url)

app.mount("/staticFiles", StaticFiles(directory='assets/staticFiles'), name='staticFiles')

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('assets/favicon.ico')


@app.api_route('/import/{import_id}', methods=["GET", "POST", "PUT", "DELETE"])
async def import_endpoint(import_id: str, request: Request):
    logger.info("Received request")
    logger.info(f"Method : {request.method}")
    static_url = str(request.url_for('staticFiles', path = 'invoice'))



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
    body = body_raw.decode('utf-8')

    generated_pdf, pdf_name, body = ubl_transform(body, _timestamp)
        
    if _page is None: 
        
        _blob_data = _blob_client.download_blob()
        content = json.loads(_blob_data.read().decode('utf-8'))
        content[str(_timestamp)] = (method, _timestamp, body, generated_pdf, pdf_name, static_url, import_id)
        
        _blob_client.upload_blob(json.dumps(content).encode('utf-8'), overwrite=True)

        return {"Response": "Succesfully added to file"}

    else:
        
        _card = CallCard(method=request.method, timestamp=_timestamp, body=body,generated_pdf=generated_pdf, pdf_name = pdf_name,static_url=static_url, page=_page, import_id=import_id)
        _page.list_page.controls.insert( 0,
            _card,
        )
        _page.update()
        _page.content[str(_timestamp)] = (request.method, _timestamp,body, generated_pdf, pdf_name, static_url, import_id)
        save_json(_page.content, _blob_client)
        return {"Response": "Succesfully received + updated app"}

@app.api_route("/import", methods=["GET", "POST", "PUT", "DELETE"])
async def read_root(request: Request):
    
    logger.info("Received request")
    logger.info(f"Method : {request.method}")
    static_url = str(request.url_for('staticFiles', path = 'invoice'))



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
    body = body_raw.decode('utf-8')

    generated_pdf, pdf_name, body = ubl_transform(body, _timestamp)
        
    if _page is None: 
        
        _blob_data = _blob_client.download_blob()
        content = json.loads(_blob_data.read().decode('utf-8'))
        content[str(_timestamp)] = (method, _timestamp, body, generated_pdf, pdf_name, static_url, None)
        
        _blob_client.upload_blob(json.dumps(content).encode('utf-8'), overwrite=True)

        return {"Response": "Succesfully added to file"}

    else:
        
        _card = CallCard(method=request.method, timestamp=_timestamp, body=body,generated_pdf=generated_pdf, pdf_name = pdf_name,static_url=static_url, page=_page)
        _page.list_page.controls.insert( 0,
            _card,
        )
        _page.update()
        _page.content[str(_timestamp)] = (request.method, _timestamp,body, generated_pdf, pdf_name, static_url, None)
        save_json(_page.content, _blob_client)
        return {"Response": "Succesfully received + updated app"}

def check_auth(username, password):
    return (_username == username) and (_password == password)


def ubl_transform(body, time):
    pdf_found = False
    file_name = None

    try:
        soup = BeautifulSoup(body, "xml")
        pdf_soup = soup.find("cbc:EmbeddedDocumentBinaryObject")
        pdf = pdf_soup.contents[0]
        pdf.replace_with(f'{pdf[0:5]}...{pdf[-6:-1]}')  
        body = create_large_prettify(soup)

        _file_name = f"{str(time).replace('.','')}.pdf"

        if pdf != None:
            path = os.path.join('assets', 'staticFiles','invoice',f'{_file_name[0:-4]}')
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path,_file_name), "wb") as f:
                f.write(base64.b64decode(pdf))
            file_name = _file_name
            pdf_found = True
            
        
    except Exception as error: 
        logger.info(f'Failed to transfor UBL:')
        logger.info(error)
        

    return pdf_found, file_name, str(body)


def create_large_prettify(soup: BeautifulSoup):
    factor = 6
    lines = soup.prettify().split('\n')
    result = ''
    for line in lines: 
        spaces = (len(line) - len(line.lstrip(' ')))
        line = factor * spaces * ' ' + line
        result += line+ '\n'

    return result


def create_list_view(page, content):

    if len(content.keys()) > 0:
        keys = list(content.keys())
        keys.sort(reverse=True)
        list_page = ft.ListView(
            expand=True,
            controls = [
                CallCard(method=method, timestamp=timestamp, body=body, generated_pdf = generated_pdf, pdf_name = pdf_name, static_url=static_url, page=page, import_id=import_id) 
                for (method, timestamp, body, generated_pdf, pdf_name, static_url, import_id) in [content[key] for key in keys]
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

    page.title = "Smart Connect API"
    page.blob_client = _blob_client

    logger.info("OPEN NEW PAGE")

    _blob_data = _blob_client.download_blob()
    page.content = json.loads(_blob_data.read().decode('utf-8'))

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

app.mount("/", flet_fastapi.app(main, assets_dir=os.path.abspath("assets")))


if __name__ == "__main__":
    uvicorn.run('main:app', host='0.0.0.0')

