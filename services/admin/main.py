from fastapi import FastAPI
from sqladmin import Admin, ModelView
from database import engine, Base
from models import User, Strategy, Subscription

# Create tables (for simplicity in dev, use Alembic in prod)
Base.metadata.create_all(bind=engine)

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
admin = Admin(app, engine, title="Crypto Strategy Admin")
admin.add_view(UserAdmin)
admin.add_view(StrategyAdmin)
admin.add_view(SubscriptionAdmin)

@app.get("/")
def root():
    return {"message": "Admin API is running. Go to /admin to manage data."}
