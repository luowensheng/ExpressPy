# Expresspy

## FastAPI Wrapper that looks like Express.js in python

```python

express = require('express')
app = express()
router = express.Router()


app.use(express.static('public'))

app.set("views", "views")

@app.get("/get/:id")
def params_test(req, res):
    res.render("index", {"id":req.params.id})


@router.post("/post")
def post_test(req, res):
    res.send("'POST request to the homepage'")


@router.all("/all")
def all_test(req, res, next):
    res.send('Accessing the secret section ...')
    next()  


@router.get("/file")
def file(req, res):
    res.sendFile("./requirements.txt")


app.use("/test", router)

app.listen(port=8000)

```
