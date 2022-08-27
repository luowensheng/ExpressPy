
from argparse import ArgumentError
import os
from pprint import pprint
import re
from typing import Callable, Union
from typing_extensions import Self
import uvicorn
from fastapi import FastAPI, Request as _Request
from js import default, Object, export
import inspect
from fastapi import responses 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


SHARED_DATA = dict()

class Next:

    def __init__(self) -> None:
        self.next = False

    def __call__(self):
        self.next = True

    def __bool__(self):
        return self.next    


def __get_methods(obj:type):

    for (name, value) in inspect.getmembers(obj):

        if "__" in name or not callable(value): continue

        yield (name, value)


def mixin(*types):

    def wrapper(cls):

        for item in types:
        
            for (name, value) in __get_methods(item):
                setattr(cls, name, value)
        
        return cls        

    return wrapper

class HTTPMethods:

    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class Request:

    params: Object

    def __init__(self, request:_Request, params:list[str]):

        self.request = request

        self.params = Object()

        if len(params) == 0: return
        
        values = request.values()

        for value in values:
            
            if not isinstance(value, dict): continue
            
            key, val = next(iter(value.items()))

            if key in params:
                self.params[key] =  val   

    def __getattr__(self, __name: str):

        return getattr(self.request, __name)    


class Response:

    def __init__(self) -> None:
        self.content = {}

    def send(self, data):
        self.content = data

    def sendFile(self, path):
        data = open(path).read()
        self.content = responses.HTMLResponse(content=data)  

    def render(self, name:str, data:dict={}):

        for val in inspect.currentframe().f_back.f_locals.values():
            
            if isinstance(val, Request):
                data['request'] = val.request
                break

        self.content = SHARED_DATA.get('views').TemplateResponse(name+".html", context=data)      




def get_params(func)->list:

    args = inspect.getfullargspec(func).args

    n_args = len(args)

    if n_args < 2 or n_args>3:
        raise ArgumentError(f"wrong number of arguments {n_args }")
    
    return args


class Pattern:
    params="(:\w+)"


class UrlPattern:

    def __init__(self, pattern:str) -> None:

        str_params = re.findall(Pattern.params, pattern)
        out_params = []
        
        for param in str_params:

            param_name = param[1:]
            out_params.append(param_name)
            updated = "{"+param_name+"}"
            pattern = pattern.replace(param, updated)

        self.pattern = pattern
        self.params = out_params

    def __repr__(self) -> str:
        return str({"pattern": self.pattern,"params": self.params })    



def get_wrapper(base, *methods, pattern:str):

    url = UrlPattern(pattern)
    
    handlers = ( getattr(base, method)(url.pattern) for method in methods )


    def wrapper(funcs:list[Callable]):

        targets = []

        for func in funcs:
        
            args = get_params(func)
            has_3_args = len(args) == 3
    
            
            def __func_2_args(request: _Request, response:Response, _:Next):
                
                func(request, response)

                return response.content 


            def __func_3_args(request: _Request, response:Response, next:Next):
                
                next.next = False

                func(request, response, next)

                return response.content
            
            target = __func_2_args if not has_3_args else __func_3_args
            targets.append(target)

        for handler in handlers:

            def fn(request: _Request):
                
                request = Request(request, params=url.params)
                response = Response()
                next = Next()
                
                content = {}

                for fn in targets:
                    content = fn(request, response, next)

                    if not next:
                        break
                
                return content


            handler(fn)  

    return wrapper


def get_all_files_from_folder(folder_path:str):

    fp = os.path.join(os.getcwd(), folder_path)

    for item in os.listdir(fp):

        yield (item, os.path.join(fp, item))


@export
def static(name:str):

    pattern = "/static"
    
    def generate(app:FastAPI):
        app.mount(pattern, StaticFiles(directory=name), name=name)

    return pattern, generate    


@export
class Router:

    def __init__(self) -> None:

        self.routes_map: dict[str, dict[str, list[Callable]]] = {}
        self.uses: dict[str] = {}
        
    def _add(self, *methods, pattern:str):

        def wrapper(func):

            for method in methods:
                
                self.routes_map[pattern] = self.routes_map.get(pattern, {})
                self.routes_map[pattern][method] = self.routes_map[pattern].get(method, [])+ []
                self.routes_map[pattern][method].append(func)

        return wrapper


    def use(self, *args):
        
        args_len = len(args)

        if args_len == 2:
           self._use_2_(args[0], args[1])
    

    def _use_2_(self, path:str, item):

        if isinstance(item, Router):
            self._combine(path, item)
            return

        if callable(item):
           self.uses[path] = item     


    def _combine(self, path:str, router:Self):

        for pattern, pattern_map in router.routes_map.items():

            new_pattern = path+pattern
            self.routes_map[new_pattern] = pattern_map


    def get(self, pattern:str):
        return self._add( HTTPMethods.GET, pattern=pattern)  

    def post(self, pattern:str):
        return self._add( HTTPMethods.POST, pattern=pattern)  

    def put(self, pattern:str):
        return self._add( HTTPMethods.PUT, pattern=pattern)  


    def delete(self, pattern:str):
        return self._add( HTTPMethods.DELETE, pattern=pattern)  

    def all(self, pattern:str):

        return self._add(  
                      HTTPMethods.DELETE, 
                      HTTPMethods.GET, 
                      HTTPMethods.POST, 
                      HTTPMethods.PUT, 
                      pattern=pattern
                )  


            
@default
class Express(Router):

    def __init__(self, *args, **kwargs):

        super().__init__()
        self.app = FastAPI(*args, **kwargs)


    def listen(self, port=8000, host="localhost"):

        self.__setup()
        uvicorn.run(self.app, host=host, port=port)

    def set(self, item, value):

        if item == 'views':
           SHARED_DATA["views"] = Jinja2Templates(directory=value)   
    
 
    def __setup(self):

        for fn in self.uses.values():
            fn(self.app)
        
        maps = self.routes_map.copy()

        for (pattern, pattern_data) in maps.items():

            for (method, routes_list) in pattern_data.items():
                
                get_wrapper(self.app, method, pattern=pattern)(routes_list)



    def show_routes(self):
        pprint(self.routes_map)
