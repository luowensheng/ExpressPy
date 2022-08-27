from inspect import ismodule
from typing_extensions import Self

true = True
false = False


class Object(dict):

    def __init__(self, **kwargs) -> None:
        
        super().__init__(kwargs)
        
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, val):
        self[key] =  val



class Module(Object):

    def __init__(self) -> None:

        super().__init__()
        self.default = lambda: None

    def __call__(self):
        return self.default()    



def require(module:str)->Module:
    
    mod =  __import__(module)

    js_mod = Module()

    for item in dir(mod):
        
        if item.startswith("__"): continue

        value = getattr(mod, item)

        if ismodule(value): continue

        if getattr(value, '__default__', False):
            js_mod.default = value
            
        
        if getattr(value, '__export__', False):
           js_mod[item] = value
    
    return js_mod



def default(item:type)->Self:

    item.__default__ = True
    return item

def export(item:type)->Self:

    item.__export__ = True
    return item
