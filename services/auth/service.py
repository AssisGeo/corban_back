from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pymongo import MongoClient
import os
from fastapi import HTTPException, status
from .schemas import UserCreate, UserResponse
from .roles.constants import UserRole, ROLE_PERMISSIONS, ROLE_NAMES

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 17000

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.users = self.db["users"]

        # Criar índices únicos
        self.users.create_index("email", unique=True)

        # Criar usuário admin se não existir
        self._create_default_admin()

    def _create_default_admin(self):
        """Cria um usuário admin padrão se não existir nenhum admin"""
        admin_exists = self.users.find_one({"role": UserRole.ADMIN})
        if not admin_exists:
            admin_user = {
                "email": "admin@exemplo.com",
                "name": "Admin",
                "hashed_password": self.get_password_hash("admin123"),
                "role": UserRole.ADMIN,
                "created_at": datetime.utcnow(),
            }
            self.users.insert_one(admin_user)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def create_user(self, user: UserCreate) -> UserResponse:
        if self.users.find_one({"email": user.email}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user_data = {
            "email": user.email,
            "name": user.name,
            "hashed_password": self.get_password_hash(user.password),
            "role": user.role,
            "created_at": datetime.utcnow(),
        }

        self.users.insert_one(user_data)

        return UserResponse(
            email=user.email,
            name=user.name,
            role=user.role,
            role_name=ROLE_NAMES.get(user.role, "Operador"),
            permissions=ROLE_PERMISSIONS.get(user.role, []),
        )

    async def authenticate_user(self, email: str, password: str):
        user = self.users.find_one({"email": email})
        if not user:
            return False
        if not self.verify_password(password, user["hashed_password"]):
            return False
        return user

    def get_current_user(self, token: str) -> UserResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = self.users.find_one({"email": email})
        if user is None:
            raise credentials_exception

        # Pegar a role do usuário ou definir como OPERATOR por padrão
        user_role = user.get("role", UserRole.OPERATOR)

        return UserResponse(
            email=user["email"],
            name=user["name"],
            role=user_role,
            role_name=ROLE_NAMES.get(user_role, "Operador"),
            permissions=ROLE_PERMISSIONS.get(user_role, []),
        )
