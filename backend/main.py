import asyncio
import json
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from backend.bot.trading_bot import TradingBot
from backend.exchange.exchange_simulator import ExchangeSimulator

app = FastAPI(title="PPO RL Crypto Trading Bot API")

# Add CORS Middleware to allow requests from the React frontend (port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global trading bot
bot = TradingBot()
bot.connect()

# Background task for running the paper trading loop
trading_task = None

@app.on_event("startup")
async def startup_event():
    global trading_task
    # Start paper trading bot loop automatically in development
    trading_task = asyncio.create_task(bot.run_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global trading_task
    bot.stop()
    if trading_task:
        trading_task.cancel()
        try:
            await trading_task
        except asyncio.CancelledError:
            pass

# Simple persistence for users in a JSON file
USERS_FILE = "users_db.json"
users_db = {}
if os.path.exists(USERS_FILE):
    try:
        with open(USERS_FILE, "r") as f:
            users_db = json.load(f)
    except Exception:
        pass

# Current active user session (mock)
current_user = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    displayName: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    global current_user
    if req.email in users_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email already registered")
    
    uid = str(uuid.uuid4())
    user_data = {
        "uid": uid,
        "email": req.email,
        "password": req.password,
        "displayName": req.displayName
    }
    users_db[req.email] = user_data
    
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users_db, f)
    except Exception:
        pass
        
    current_user = {
        "uid": uid,
        "email": req.email,
        "displayName": req.displayName
    }
    return current_user

@app.post("/api/auth/login")
def login(req: LoginRequest):
    global current_user
    user_data = users_db.get(req.email)
    if not user_data or user_data["password"] != req.password:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    current_user = {
        "uid": user_data["uid"],
        "email": user_data["email"],
        "displayName": user_data["displayName"]
    }
    return current_user

@app.post("/api/auth/logout")
def logout():
    global current_user
    current_user = None
    return {"status": "success"}

@app.get("/api/auth/me")
def get_me():
    return current_user

class BacktestRequest(BaseModel):
    pair: str
    timeframe: str
    initialBalance: float

class SignalRequest(BaseModel):
    pair: str
    leverage: int = 10
    capital: float = 100

@app.get("/api/status")
def get_status():
    status = bot.get_status()
    # Add agent metrics
    metrics = bot.agent.get_metrics()
    return {
        "botStatus": status["botStatus"],
        "exchangeStatus": "CONNECTED",
        "strategyStatus": {
            "rsiOverbought": 70,
            "rsiOversold": 30,
            "ppoThreshold": 0.05,
            "confidenceThreshold": 0.2
        },
        "rlStatus": metrics
    }

@app.get("/api/trades")
def get_trades():
    return bot.get_trades()

@app.get("/api/signals")
def get_signals():
    return bot.get_signals()

@app.get("/api/pairs")
def get_pairs():
    return bot.exchange.get_trading_pairs()

@app.get("/api/market-data/{pair}")
def get_market_data(pair: str):
    # Retrieve single pair ticker price
    return bot.exchange.get_market_data(pair)

@app.post("/api/signal")
async def generate_signal(req: SignalRequest):
    signal = await bot.get_trading_signal(req.pair)
    return signal

@app.post("/api/backtest")
async def start_backtest(req: BacktestRequest):
    results = await bot.execute_backtest(req.model_dump())
    return results

@app.get("/api/performance")
def get_performance():
    # Return dummy/metrics comparison
    return {
        "backtest": {
            "totalPnL": 15.5,
            "winRate": 65,
            "totalTrades": 100,
            "averagePnL": 0.155
        },
        "forwardTest": {
            "totalTrades": len(bot.trades),
            "winningTrades": sum(1 for t in bot.trades if t.get("pnl", 0) > 0),
            "losingTrades": sum(1 for t in bot.trades if t.get("pnl", 0) < 0),
            "winRate": (sum(1 for t in bot.trades if t.get("pnl", 0) > 0) / len(bot.trades) * 100) if bot.trades else 100.0,
            "totalPnL": sum(t.get("pnl", 0) for t in bot.trades),
            "maxDrawdown": 0.02
        },
        "accuracy": 0.72
    }

# Track active WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial data immediately
        initial_data = {
            "type": "initial",
            "status": {
                "botStatus": "RUNNING" if bot.is_running else "STOPPED",
                "exchangeStatus": "CONNECTED",
                "strategyStatus": {
                    "rsiOverbought": 70,
                    "rsiOversold": 30,
                    "ppoThreshold": 0.05,
                    "confidenceThreshold": 0.2
                },
                "rlStatus": bot.agent.get_metrics()
            },
            "trades": bot.get_trades(),
            "signals": bot.get_signals(),
            "performance": {
                "backtest": {
                    "totalPnL": 15.5,
                    "winRate": 65,
                    "totalTrades": 100,
                    "averagePnL": 0.155
                },
                "forwardTest": {
                    "totalTrades": len(bot.trades),
                    "winningTrades": sum(1 for t in bot.trades if t.get("pnl", 0) > 0),
                    "losingTrades": sum(1 for t in bot.trades if t.get("pnl", 0) < 0),
                    "winRate": (sum(1 for t in bot.trades if t.get("pnl", 0) > 0) / len(bot.trades) * 100) if bot.trades else 100.0,
                    "totalPnL": sum(t.get("pnl", 0) for t in bot.trades),
                    "maxDrawdown": 0.02
                },
                "accuracy": 0.72
            }
        }
        await websocket.send_text(json.dumps(initial_data))

        # Periodic streaming loop
        while True:
            # Send live updates every 5 seconds
            await asyncio.sleep(5)
            update_data = {
                "type": "update",
                "status": {
                    "botStatus": "RUNNING" if bot.is_running else "STOPPED",
                    "exchangeStatus": "CONNECTED",
                    "strategyStatus": {
                        "rsiOverbought": 70,
                        "rsiOversold": 30,
                        "ppoThreshold": 0.05,
                        "confidenceThreshold": 0.2
                    },
                    "rlStatus": bot.agent.get_metrics()
                },
                "trades": bot.get_trades(),
                "signals": bot.get_signals(),
                "performance": {
                    "backtest": {
                        "totalPnL": 15.5,
                        "winRate": 65,
                        "totalTrades": 100,
                        "averagePnL": 0.155
                    },
                    "forwardTest": {
                        "totalTrades": len(bot.trades),
                        "winningTrades": sum(1 for t in bot.trades if t.get("pnl", 0) > 0),
                        "losingTrades": sum(1 for t in bot.trades if t.get("pnl", 0) < 0),
                        "winRate": (sum(1 for t in bot.trades if t.get("pnl", 0) > 0) / len(bot.trades) * 100) if bot.trades else 100.0,
                        "totalPnL": sum(t.get("pnl", 0) for t in bot.trades),
                        "maxDrawdown": 0.02
                    },
                    "accuracy": 0.72
                }
            }
            await websocket.send_text(json.dumps(update_data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
