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
from services.inapi.router import router as inapi_router
from services.bmg.router import router as bmg_router
import uvicorn
from services.evolution.router import router as evolution_router
from services.simulations.proposal_router import router as proposal_router
from services.bmg.card_router import router as card_router
from services.simulations.batch_router import router as batch_simulation_router


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
    # allow_origins=["https://app.ar4finance.com.br"],
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
app.include_router(inapi_router)
app.include_router(bmg_router)
app.include_router(evolution_router)
app.include_router(proposal_router)
app.include_router(card_router)
app.include_router(batch_simulation_router)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)
