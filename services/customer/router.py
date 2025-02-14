from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from .service import CustomerService
from .schemas import CustomerUpdate, CustomerUploadResponse, CustomerListResponse
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("/upload", response_model=CustomerUploadResponse)
async def upload_customers(
    file: UploadFile = File(...), service: CustomerService = Depends()
):
    """Upload customer data from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        result = await service.process_csv(file)
        return CustomerUploadResponse(
            message="Customers processed successfully", **result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=Dict[str, Any])
async def list_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=None),
    service: CustomerService = Depends(),
):
    """List customers with pagination and search."""
    try:
        return await service.get_customers(skip, limit, search)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}", response_model=Dict[str, str])
async def update_customer(
    session_id: str, customer_data: CustomerUpdate, service: CustomerService = Depends()
):
    """Update customer data."""
    try:
        return await service.update_customer(
            session_id, customer_data.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}", response_model=Dict[str, str])
async def delete_customer(session_id: str, service: CustomerService = Depends()):
    """Delete customer."""
    try:
        return await service.delete_customer(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=CustomerListResponse)
async def get_customers_list(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=None),
    service: CustomerService = Depends(),
):
    """List customers with pagination and search."""
    try:
        skip = (page - 1) * per_page
        result = await service.get_customers(skip, per_page, search)
        return CustomerListResponse(
            customers=result.customers,
            total=result.total,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
