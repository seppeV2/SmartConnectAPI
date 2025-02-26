import flet.fastapi as flet_fastapi
from fastapi import Request, HTTPException
import flet as ft
import json
import base64
import datetime
import uvicorn

_username = "9ASmartConnectUSER"
_password = "9APass@word01"
_page = None

app = flet_fastapi.FastAPI()

@app.api_route("/import", methods=["GET", "POST", "PUT", "DELETE"])
async def read_root(request: Request):
    if _page is None: raise HTTPException(status_code=500, detail="Server not running ...")
    _basicAuth = str(request.headers['authorization']).split(' ')[-1]

    decoded_auth = base64.b64decode(_basicAuth).decode('utf8')
    (decoded_auth_usr, decoded_auth_passwd) = (decoded_auth.split(':')[0], decoded_auth.split(':')[1])

    if not check_auth(decoded_auth_usr, decoded_auth_passwd):
        raise HTTPException(status_code=401, detail="Unauthorized access")
    
    else:
        body_raw = await request.body()
        body = json.loads(body_raw.decode('utf-8'))
        _timestamp = datetime.datetime.now().timestamp()
        _card = CallCard(method=request.method, timestamp=_timestamp, body=body, page=_page)
        _page.list_page.controls.insert( 0,
            _card,
        )
        _page.update()
        _page.content[_timestamp] = (request.method, _timestamp,body)
        save_json(_page.content)
        return {"Response": "Succesfully received"}

def check_auth(username, password):
    return (_username == username) and (_password == password)



def delete_request(e, tile, listView, page, timestamp):
    listView.controls.remove(tile)
    page.content.pop(timestamp)
    save_json(page.content)
    page.update()

class CallCard(ft.Container):
    
    def __init__(self, method, timestamp, body, page):
        self.method = method
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)
        self.timestamp_s = timestamp
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
            content = ft.Text(body),
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

async def main(page: ft.Page):
    global _page
    _page = page

    with open('content.json', 'r') as file: 
        page.content = json.load(file)

    

    _page.list_page = ft.ListView(
        expand=True,
        controls = [
            CallCard(method=method, timestamp=timestamp, body=body, page=page) 
            for (method, timestamp, body) in [page.content[key] for key in page.content.keys()]
        ],
    )

    _appbar = ft.AppBar(
        leading = ft.Text(),
        title= ft.SafeArea(
            content= ft.Text(
                value='Smart Connect API Test Page', 
                text_align=ft.TextAlign.CENTER,
                size=40,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,            
            ),
        ),
        center_title = True,
    )

    page.views[-1].appbar = _appbar
    page.views[-1].controls.append(
        ft.Divider(thickness=3, color=ft.Colors.WHITE)
    )
    page.views[-1].controls.append(
        _page.list_page
    )

    page.update()

app.mount("/", flet_fastapi.app(main))

if __name__ == "__main__":
    uvicorn.run('main:app', host='0.0.0.0', port=8000)

