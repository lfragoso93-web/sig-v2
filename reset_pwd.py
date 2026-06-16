from passlib.context import CryptContext
ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
novo_hash = ctx.hash("Admin@123")
print(novo_hash)