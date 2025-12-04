from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from database import engine, Base, settings
from models import User, Strategy, Subscription, Signal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from database import get_db
from sqlalchemy import func
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
    column_list = [User.id, User.telegram_id, User.username, User.balance, User.is_active, User.subscriptions]
    column_searchable_list = [User.username, User.telegram_id]
    form_columns = [User.telegram_id, User.username, User.full_name, User.balance, User.is_active]
    icon = "fa-solid fa-user"
    
    # async def _format_subscriptions(self, model, attribute):
    #     """Display subscription strategies for each user"""
    #     if not model.subscriptions:
    #         return "无"
    #     active_subs = [s for s in model.subscriptions if s.is_active]
    #     if not active_subs:
    #         return "无"
    #     strategy_names = ", ".join([s.strategy.name for s in active_subs])
    #     return strategy_names
    
    # column_formatters = {
    #     "subscriptions": _format_subscriptions
    # }

class StrategyAdmin(ModelView, model=Strategy):
    column_list = [Strategy.id, Strategy.name, Strategy.price_monthly, Strategy.is_active]
    form_columns = [Strategy.name, Strategy.description, Strategy.price_monthly, Strategy.config_json, Strategy.is_active]
    icon = "fa-solid fa-chart-line"

class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [Subscription.id, Subscription.user, Subscription.strategy, Subscription.is_active]
    icon = "fa-solid fa-ticket"

class SignalAdmin(ModelView, model=Signal):
    column_list = [Signal.id, Signal.strategy, Signal.symbol, Signal.side, Signal.price, Signal.timestamp]
    column_sortable_list = [Signal.timestamp]
    icon = "fa-solid fa-signal"
    can_create = False # Signals are created by the engine, not manually
    can_edit = False
    can_delete = True

# --- Setup Admin ---
admin = Admin(app, engine, title="Crypto Strategy Admin", authentication_backend=authentication_backend)
admin.add_view(UserAdmin)
admin.add_view(StrategyAdmin)
admin.add_view(SubscriptionAdmin)
admin.add_view(SignalAdmin)

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

@app.get("/users/{telegram_id}")
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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

@app.get("/strategies/{strategy_id}/subscribers")
def get_strategy_subscribers(strategy_id: int, db: Session = Depends(get_db)):
    """Get all active subscribers for a strategy"""
    subscriptions = db.query(models.Subscription).filter(
        models.Subscription.strategy_id == strategy_id,
        models.Subscription.is_active == True
    ).all()
    
    subscribers = []
    for sub in subscriptions:
        if sub.user and sub.user.is_active:
            subscribers.append({
                "telegram_id": sub.user.telegram_id,
                "username": sub.user.username
            })
    return subscribers

@app.get("/strategies/")
def list_strategies(db: Session = Depends(get_db)):
    return db.query(models.Strategy).filter(models.Strategy.is_active == True).all()

class SubscriptionCreate(BaseModel):
    telegram_id: str
    strategy_id: int

@app.post("/subscriptions/")
def create_subscription(sub: SubscriptionCreate, db: Session = Depends(get_db)):
    try:
        # Lock user row to prevent race conditions
        user = db.query(models.User).filter(models.User.telegram_id == sub.telegram_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        strategy = db.query(models.Strategy).filter(models.Strategy.id == sub.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Double-check: Requery with lock to ensure no concurrent subscription
        existing = db.query(models.Subscription).filter(
            models.Subscription.user_id == user.id,
            models.Subscription.strategy_id == strategy.id,
            models.Subscription.is_active == True
        ).with_for_update().first()
        
        if existing:
            return {"message": "Already subscribed", "status": "exists"}

        # Check balance
        if user.balance < strategy.price_monthly:
            return {
                "message": f"Insufficient balance. Required: ${strategy.price_monthly:.2f}, Available: ${user.balance:.2f}",
                "status": "insufficient_balance",
                "required": strategy.price_monthly,
                "available": user.balance
            }

        # Deduct balance
        user.balance -= strategy.price_monthly
        db.add(user)

        # Create subscription
        new_sub = models.Subscription(
            user_id=user.id,
            strategy_id=strategy.id,
            is_active=True
        )
        db.add(new_sub)
        db.commit()
        return {"message": "Subscription created", "status": "created", "remaining_balance": user.balance}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


