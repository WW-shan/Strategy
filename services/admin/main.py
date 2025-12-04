from fastapi import FastAPI, BackgroundTasks
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from database import engine, Base, settings, SessionLocal
from models import User, Strategy, Subscription, Signal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from database import get_db
from sqlalchemy import func
import models
from datetime import datetime, timedelta
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    form_columns = [User.telegram_id, User.username, User.full_name, User.balance, User.is_active]
    icon = "fa-solid fa-user"

class StrategyAdmin(ModelView, model=Strategy):
    column_list = [Strategy.id, Strategy.name, Strategy.price_monthly, Strategy.is_active]
    form_columns = [Strategy.name, Strategy.description, Strategy.price_monthly, Strategy.config_json, Strategy.is_active]
    icon = "fa-solid fa-chart-line"

class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [Subscription.id, Subscription.user, Subscription.strategy, Subscription.start_date, Subscription.end_date, Subscription.is_active]
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
    """Get all active subscribers for a strategy (checks expiration)"""
    now = datetime.utcnow()
    subscriptions = db.query(models.Subscription).filter(
        models.Subscription.strategy_id == strategy_id,
        models.Subscription.is_active == True
    ).all()
    
    subscribers = []
    for sub in subscriptions:
        # Check if subscription has expired
        if sub.end_date and sub.end_date < now:
            # Auto-expire the subscription
            sub.is_active = False
            db.add(sub)
            continue
            
        if sub.user and sub.user.is_active:
            subscribers.append({
                "telegram_id": sub.user.telegram_id,
                "username": sub.user.username
            })
    
    db.commit()
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

        # Create subscription with end_date (30 days from now)
        end_date = datetime.utcnow() + timedelta(days=30)
        new_sub = models.Subscription(
            user_id=user.id,
            strategy_id=strategy.id,
            is_active=True,
            start_date=datetime.utcnow(),
            end_date=end_date
        )
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        
        return {
            "message": "Subscription created", 
            "status": "created", 
            "remaining_balance": user.balance,
            "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

class SubscriptionRenew(BaseModel):
    telegram_id: str
    strategy_id: int

@app.post("/subscriptions/renew")
def renew_subscription(renew: SubscriptionRenew, db: Session = Depends(get_db)):
    """Renew an existing subscription (extend by 30 days)"""
    try:
        user = db.query(models.User).filter(models.User.telegram_id == renew.telegram_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        strategy = db.query(models.Strategy).filter(models.Strategy.id == renew.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # Find existing subscription
        subscription = db.query(models.Subscription).filter(
            models.Subscription.user_id == user.id,
            models.Subscription.strategy_id == strategy.id
        ).order_by(models.Subscription.id.desc()).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")
        
        # Check balance
        if user.balance < strategy.price_monthly:
            return {
                "message": f"余额不足。需要: ${strategy.price_monthly:.2f}，可用: ${user.balance:.2f}",
                "status": "insufficient_balance",
                "required": strategy.price_monthly,
                "available": user.balance
            }
        
        # Deduct balance
        user.balance -= strategy.price_monthly
        
        # Extend subscription
        now = datetime.utcnow()
        if subscription.end_date and subscription.end_date > now:
            # Still active, extend from current end_date
            new_end_date = subscription.end_date + timedelta(days=30)
        else:
            # Expired, extend from now
            new_end_date = now + timedelta(days=30)
        
        subscription.end_date = new_end_date
        subscription.is_active = True
        
        db.add(user)
        db.add(subscription)
        db.commit()
        
        return {
            "message": "续订成功",
            "status": "renewed",
            "remaining_balance": user.balance,
            "new_end_date": new_end_date.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")

def check_expired_subscriptions():
    """Background task to check and deactivate expired subscriptions"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired_subs = db.query(models.Subscription).filter(
            models.Subscription.is_active == True,
            models.Subscription.end_date != None,
            models.Subscription.end_date < now
        ).all()
        
        if expired_subs:
            logger.info(f"Found {len(expired_subs)} expired subscriptions, deactivating...")
            for sub in expired_subs:
                sub.is_active = False
                db.add(sub)
            db.commit()
            logger.info(f"Deactivated {len(expired_subs)} expired subscriptions")
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}")
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    """Start background task for checking expired subscriptions"""
    async def periodic_expiry_check():
        while True:
            check_expired_subscriptions()
            await asyncio.sleep(3600)  # Check every hour
    
    asyncio.create_task(periodic_expiry_check())
    logger.info("Started periodic subscription expiry checker")


