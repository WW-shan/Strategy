from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from database import engine, Base, settings
from models import User, Strategy, Subscription
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
import models

# Create tables (for simplicity in dev, use Alembic in prod)
Base.metadata.create_all(bind=engine)

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"token": "admin_token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

app = FastAPI(title="Strategy Admin Panel")

# --- SQLAdmin Views ---
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.telegram_id, User.username, User.balance, User.is_active]
    column_searchable_list = [User.username, User.telegram_id]
    icon = "fa-solid fa-user"

class StrategyAdmin(ModelView, model=Strategy):
    column_list = [Strategy.id, Strategy.name, Strategy.price_monthly, Strategy.is_active]
    form_columns = [Strategy.name, Strategy.description, Strategy.price_monthly, Strategy.config_json, Strategy.is_active]
    icon = "fa-solid fa-chart-line"

class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [Subscription.id, Subscription.user, Subscription.strategy, Subscription.is_active]
    icon = "fa-solid fa-ticket"

# --- Setup Admin ---
admin = Admin(app, engine, title="Crypto Strategy Admin", authentication_backend=authentication_backend)
admin.add_view(UserAdmin)
admin.add_view(StrategyAdmin)
admin.add_view(SubscriptionAdmin)

class UserCreate(BaseModel):
    telegram_id: str
    username: str | None = None
    full_name: str | None = None

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.telegram_id == user.telegram_id).first()
    if db_user:
        # Update info if changed
        if db_user.username != user.username:
            db_user.username = user.username
        if db_user.full_name != user.full_name:
            db_user.full_name = user.full_name
        db.commit()
        return db_user
    
    new_user = models.User(telegram_id=user.telegram_id, username=user.username, full_name=user.full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/{telegram_id}/subscriptions")
def get_user_subscriptions(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    # Return simplified list
    result = []
    for sub in user.subscriptions:
        if sub.is_active:
            result.append({
                "strategy_name": sub.strategy.name,
                "end_date": sub.end_date.strftime("%Y-%m-%d") if sub.end_date else "Lifetime"
            })
    return result

@app.get("/strategies/")
def list_strategies(db: Session = Depends(get_db)):
    return db.query(models.Strategy).filter(models.Strategy.is_active == True).all()

