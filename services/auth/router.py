from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from .service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from .schemas import Token, UserCreate, UserResponse
from .roles.constants import UserRole, ROLE_PERMISSIONS, ROLE_NAMES

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), auth_service: AuthService = Depends()
) -> UserResponse:
    return auth_service.get_current_user(token)


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, auth_service: AuthService = Depends()):
    """Registra um novo usuário"""
    return await auth_service.create_user(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(),
):
    """Autentica um usuário e retorna o token com suas permissões"""
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )

    # Pegar role e permissões do usuário
    user_role = user.get("role", UserRole.OPERATOR)
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    role_name = ROLE_NAMES.get(user_role, "Operador")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"role": user_role, "permissions": permissions, "role_name": role_name},
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """Retorna informações do usuário logado"""
    return current_user
