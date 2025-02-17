from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from services.document_upload.router import router as document_router
from services.customer.router import router as customer_router
from services.chat.router import router as chat_router
from services.auth.router import router as auth_router
from services.simulations.router import router as simulation_router
from services.simulations.banks_router import router as banks_router
from services.vctex.router import router as vctex_router
from services.cep.router import router as cep_router
from services.sessions.router import router as session_router

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DECOTECH API FGTS",
    version="1.0",
    description="Decotech System.",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação"""
    error_details = []
    for error in exc.errors():
        error_details.append(
            {
                "loc": " -> ".join(str(loc) for loc in error["loc"]),
                "msg": error["msg"],
                "type": error["type"],
            }
        )
    logger.error(f"Validation error: {error_details}")
    return JSONResponse(
        status_code=422,
        content={"detail": error_details},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router)
app.include_router(customer_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(simulation_router)
app.include_router(banks_router)
app.include_router(vctex_router)
app.include_router(cep_router)
app.include_router(session_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002, timeout_keep_alive=300)
